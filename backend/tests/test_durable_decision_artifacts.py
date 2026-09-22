"""Persistence is checked across independent connections and a fresh process."""
import os
import subprocess
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.models.decision_artifact import DecisionArtifact
from app.services import decision_result_store as store


@pytest.fixture
def artifact_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'shared.db'}"
    engine = create_engine(url)
    DecisionArtifact.__table__.create(engine)
    monkeypatch.setattr(store, "SessionLocal", sessionmaker(bind=engine))
    yield url, engine
    engine.dispose()


def test_restart_and_other_worker_reuse_exact_snapshot(artifact_db):
    url, engine = artifact_db
    payload = {"needs": [{"parameter_id": "adl_support", "desired_value": "YES"}]}
    token = store.remember_decision_result(payload, inputs_fingerprint="case-a")
    payload["needs"].clear()
    engine.dispose()
    env = {**os.environ, "DATABASE_URL": url}
    child = subprocess.run([sys.executable, "-c", """
import sys
from app.services.decision_result_store import recall_decision_result
p = recall_decision_result(sys.argv[1], inputs_fingerprint='case-a')
assert p['needs'] == [{'parameter_id': 'adl_support', 'desired_value': 'YES'}]
assert recall_decision_result(sys.argv[1], inputs_fingerprint='case-b') is None
print('snapshot survived a new process')
""", token], env=env, text=True, capture_output=True, timeout=20)
    assert child.returncode == 0, child.stderr
    assert "snapshot survived" in child.stdout
    with store.SessionLocal() as db:
        row = db.query(DecisionArtifact).one()
        assert row.token_hash != token
        assert token not in row.payload_json


def test_independent_copies_expiry_and_schema_version(artifact_db):
    token = store.remember_decision_result({"needs": ["original"]}, inputs_fingerprint="case")
    first = store.recall_decision_result(token, inputs_fingerprint="case")
    first["needs"].clear()
    assert store.recall_decision_result(token, inputs_fingerprint="case")["needs"] == ["original"]
    with patch.object(store, "_SCHEMA_VERSION", 99):
        assert store.recall_decision_result(token, inputs_fingerprint="case") is None
    with patch.object(store.time, "time", return_value=store.time.time() + store._TTL_SECONDS + 1):
        assert store.recall_decision_result(token, inputs_fingerprint="case") is None
    with store.SessionLocal() as db:
        assert db.query(DecisionArtifact).count() == 0


def test_database_error_does_not_issue_or_silently_rebuild_handle(artifact_db):
    failure = OperationalError("unavailable", {}, Exception("offline"))
    with patch.object(store, "SessionLocal", side_effect=failure):
        with pytest.raises(store.ArtifactStoreUnavailable):
            store.remember_decision_result({}, inputs_fingerprint="case")
        with pytest.raises(store.ArtifactStoreUnavailable):
            store.recall_decision_result("existing", inputs_fingerprint="case")


def test_database_failure_returns_retryable_error_without_exposing_sql(artifact_db):
    from fastapi.testclient import TestClient
    from app import main
    profile = {"decision_intelligence": {"canonical_decision_state": {
        "authoritative": True, "client": "COMPLETE", "system": "READY"}}}
    with patch.object(main, "build_patient_needs_profile", return_value=profile), \
         patch.object(store, "SessionLocal", side_effect=OperationalError("secret SQL", {}, Exception("offline"))):
        response = TestClient(main.app).post('/decision-engine/patient-needs-profile', json={"questionnaire_state": {}})
    assert response.status_code == 503
    assert response.headers['retry-after'] == '5'
    assert 'secret SQL' not in response.text
    assert 'intake_profile_id' not in response.text

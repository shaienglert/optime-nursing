import asyncio
import json
from copy import deepcopy

import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.decision_artifact import DecisionArtifact
from app.models.search_ranking_audit import SearchRankingAudit
from app.services import decision_result_store as store
from app.services.regulatory_quality_layer import rank_with_evidence_layer
from app.services.search_ranking_admin_api import search_ranking_router
from app.services.search_ranking_audit import (
    build_search_ranking_audit, capture_search_ranking_audit, observe_final_ranking,
)


def ranked_result(count=12):
    candidates = [{"canonical_facility_id": str(i), "facility_name": f"Home {i}",
                   "budget_exception": False,
                   "regulatory_quality_evidence": {"inspection_rating": {"value": 5 - i % 3, "source_family": "CMS"}},
                   "client_intent_fit": {"must_pass": ["CARE"], "nice_unknown": ["GARDEN"]}}
                  for i in range(count)]
    ranked = rank_with_evidence_layer(candidates, lambda r: (0,), base_dimensions=(("budget_band", "budget first"),))
    return {"results": ranked, "total_candidates_scored": 50, "decision_pipeline_trace": {"status": "COMPLETE"},
            "patient_needs_profile": {"private": "not for audit"}, "query": "private narrative"}


def test_snapshot_uses_actual_comparator_without_weights_or_mutation():
    result = ranked_result()
    before = deepcopy(result)
    audit = build_search_ranking_audit(result)
    assert result == before
    assert [r["facility_id"] for r in audit["rows"]] == [r["canonical_facility_id"] for r in result["results"][:10]]
    assert audit["returned_count"] == 12
    assert audit["numeric_weights_available"] is False
    assert "private narrative" not in json.dumps(audit)
    assert "not for audit" not in json.dumps(audit)
    first = audit["rows"][0]
    assert first["criteria"][0]["value"] == 0
    inspection = next(c for c in first["criteria"] if c["parameter"] == "inspection_rating")
    assert inspection["source"] == "CMS" and inspection["role"] == "USED_TO_SEPARATE"
    assert all(c["numeric_weight"] is None for c in first["criteria"])
    result["results"][0]["__rank_comparison_trace"]["measure_values"].clear()
    assert inspection["value"] == 5


def test_unknown_is_not_invented_weight_or_negative_and_missing_snapshot_is_explicit():
    result = ranked_result(2)
    result["results"][0].pop("__rank_comparison_trace")
    row = build_search_ranking_audit(result)["rows"][0]
    assert row["snapshot_status"] == "UNAVAILABLE"
    assert all(c["role"] == "NOT_USED_TO_SEPARATE" and c["priority"] is None for c in row["criteria"])
    assert all(c["value"] is None for c in row["criteria"])
    assert build_search_ranking_audit({"results": []})["rows"] == []


def test_true_tie_and_unknown_evidence_remain_explicit():
    candidates = [{"canonical_facility_id": "a", "rank_display": "Joint #1", "rank_tie_status": "JOINT_RANK"},
                  {"canonical_facility_id": "b", "rank_display": "Joint #1", "rank_tie_status": "JOINT_RANK",
                   "regulatory_quality_evidence": {"inspection_rating": {"value": 5, "source_family": "CMS"}}}]
    ranked = rank_with_evidence_layer(candidates, lambda r: (0,), base_dimensions=(("fit", "fit first"),))
    audit = build_search_ranking_audit({"results": ranked})
    assert all(r["tie_status"] == "JOINT_RANK" for r in audit["rows"])
    assert not any(c["role"] == "USED_TO_SEPARATE" for r in audit["rows"] for c in r["criteria"])
    assert audit["rows"][0]["criteria"][4]["numeric_weight"] is None


def test_capture_is_request_local_and_resets_after_exception():
    async def request(label):
        with capture_search_ranking_audit() as capture:
            await asyncio.sleep(0)
            observe_final_ranking({"results": [{"facility_name": label}]})
            await asyncio.sleep(0)
            return capture["rows"][0]["facility_name"]
    async def concurrent():
        return await asyncio.gather(request("a"), request("b"))
    assert asyncio.run(concurrent()) == ["a", "b"]
    with pytest.raises(ValueError):
        with capture_search_ranking_audit() as capture:
            raise ValueError()
    observe_final_ranking(ranked_result())
    assert capture == {}


@pytest.fixture
def sessions(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(store, "SessionLocal", factory)
    yield factory
    engine.dispose()


def test_audit_survives_expiry_and_never_leaks_in_recalled_family_result(sessions, monkeypatch):
    monkeypatch.setattr(store.time, "time", lambda: 1000)
    token = store.remember_decision_result({"results": []}, inputs_fingerprint="x", ranking_audit=ranked_result(0))
    assert store.recall_decision_result(token, inputs_fingerprint="x") == {"results": []}
    with sessions() as db:
        record = db.query(SearchRankingAudit).one()
        assert record.decision_token_hash != token
        assert token not in record.payload_json
    monkeypatch.setattr(store.time, "time", lambda: 1000 + 7201)
    store.remember_decision_result({"artifact_kind": "INTAKE"}, inputs_fingerprint="y")
    with sessions() as db:
        assert db.query(SearchRankingAudit).count() == 1
        assert db.query(DecisionArtifact).count() == 1


def test_audit_failure_rolls_back_decision_handle(sessions, monkeypatch):
    # Simulate unavailable audit storage with the real transaction, not a mock commit.
    with sessions() as db:
        SearchRankingAudit.__table__.drop(db.get_bind())
    with pytest.raises(store.ArtifactStoreUnavailable):
        store.remember_decision_result({"results": []}, inputs_fingerprint="x", ranking_audit={"rows": []})
    with sessions() as db:
        assert db.query(DecisionArtifact).count() == 0


def test_admin_api_requires_gate_paginates_and_sends_no_store(sessions):
    def require_admin(x_admin_token: str | None = Header(default=None)):
        if x_admin_token != "test-only":
            raise HTTPException(401)
    def get_db():
        with sessions() as db:
            yield db
    app = FastAPI()
    app.include_router(search_ranking_router(require_admin, get_db))
    for i in range(3):
        store.remember_decision_result({"results": []}, inputs_fingerprint=str(i), ranking_audit=build_search_ranking_audit(ranked_result(2)))
    client = TestClient(app)
    path = "/api/admin/search-ranking-audits"
    assert client.get(path).status_code == 401
    assert client.get(path + "/unknown").status_code == 401
    headers = {"x-admin-token": "test-only"}
    response = client.get(path + "?limit=2", headers=headers)
    assert response.headers["cache-control"] == "no-store"
    first = response.json()
    assert len(first["items"]) == 2 and first["has_more"]
    second = client.get(path + "?limit=2&offset=2", headers=headers).json()
    assert len(second["items"]) == 1 and not second["has_more"]
    assert not set(x["id"] for x in first["items"]) & set(x["id"] for x in second["items"])
    detail = client.get(path + "/" + first["items"][0]["id"], headers=headers)
    assert len(detail.json()["rows"]) == 2
    assert "decision_token_hash" not in detail.text
    assert client.get(path + "/unknown", headers=headers).status_code == 404
    assert client.get(path + "?limit=1000", headers=headers).status_code == 422

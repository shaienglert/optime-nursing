import json
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models.agent_execution import SupervisorIncidentLog
from app.services import user_incident_reporting as service


@pytest.fixture
def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SupervisorIncidentLog.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    with patch.object(service, "SessionLocal", factory):
        yield factory
    engine.dispose()


def test_event_is_durable_sanitized_and_wakes_immediately(database):
    service.wake.clear()
    event = service.record_incident(kind="SERVER_HTTP_ERROR", path="/facilities/private-token?email=secret", status=500)
    assert service.wake.is_set()
    with database() as db:
        row = db.query(SupervisorIncidentLog).one()
        data = json.loads(row.details_json)
        assert data["event_id"] == event
        assert data["path"] == "/facilities"
        assert "private-token" not in row.details_json and "secret" not in row.details_json


def test_accepted_mail_is_owner_only_and_does_not_repeat(database):
    service.record_incident(kind="SERVER_EXCEPTION", path="/results", status=500)
    with patch.object(service, "send_email_detailed", return_value=SimpleNamespace(ok=True, status="DELIVERY_ACCEPTED")) as send:
        assert service.deliver_pending() == 1
        assert service.deliver_pending() == 0
        assert send.call_count == 1
        assert send.call_args.kwargs["recipients"] == ["shaienglert@gmail.com"]
    with database() as db:
        assert db.query(SupervisorIncidentLog).one().status == "NOTIFIED"


def test_failed_mail_stays_durable_and_is_retried(database):
    service.record_incident(kind="SERVER_EXCEPTION", path="/results")
    with patch.object(service, "send_email_detailed", return_value=SimpleNamespace(ok=False, status="DELIVERY_BLOCKED")):
        assert service.deliver_pending() == 0
    with database() as db:
        row = db.query(SupervisorIncidentLog).one()
        assert row.status == "PENDING"
        data = json.loads(row.details_json)
        assert data["delivery"] == "DELIVERY_BLOCKED"
        data["retry_at"] = 0
        row.details_json = json.dumps(data)
        db.commit()
    with patch.object(service, "send_email_detailed", return_value=SimpleNamespace(ok=True, status="DELIVERY_ACCEPTED")):
        assert service.deliver_pending() == 1


def test_duplicate_client_event_is_not_reinserted(database):
    event = str(uuid4())
    service.record_incident(kind="CLIENT_RUNTIME_ERROR", path="/results", event_id=event)
    service.record_incident(kind="CLIENT_RUNTIME_ERROR", path="/results", event_id=event)
    with database() as db:
        assert db.query(SupervisorIncidentLog).count() == 1


def test_middleware_and_origin_boundary(database):
    app = FastAPI()
    service.install_incident_reporting(app, ["https://optime-nursing.vercel.app"])
    @app.get("/broken")
    def broken():
        raise ValueError("private family text")
    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/broken").status_code == 500
    body = {"kind": "CLIENT_RUNTIME_ERROR", "page": "/results", "event_id": str(uuid4())}
    assert client.post("/api/user-incidents", json=body).status_code == 403
    assert client.post("/api/user-incidents", json=body, headers={"origin": "https://optime-nursing.vercel.app"}).status_code == 202
    with database() as db:
        rows = db.query(SupervisorIncidentLog).all()
        assert len(rows) == 2
        assert all("private family text" not in row.details_json for row in rows)


def test_reporting_failure_does_not_replace_original_exception():
    app = FastAPI()
    service.install_incident_reporting(app, [])
    @app.get("/broken")
    def broken():
        raise ValueError("original")
    with patch.object(service, "record_incident", side_effect=RuntimeError("database down")):
        with pytest.raises(ValueError, match="original"):
            TestClient(app).get("/broken")

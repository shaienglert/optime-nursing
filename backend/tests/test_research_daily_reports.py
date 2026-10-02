from datetime import date, datetime, timezone
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, RecommendationKnowledgeUsageLog
from app.services.research_daily_reports import archive_daily_report, build_daily_report, daily_report_history

NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    for model in (AgentJobRun, AgentKnowledgeRecord, RecommendationKnowledgeUsageLog):
        model.__table__.create(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


def test_no_activity_is_missing_not_healthy(db):
    report = build_daily_report(db, NOW.date(), NOW)
    assert report["status"] == "PARTIAL"
    assert all(a["status"] == "MISSING" for a in report["agents"])
    assert all(a["engine_adopted_facts"] is None for a in report["agents"])


def test_ingestion_and_guard_permission_are_not_adoption(db):
    db.add(AgentKnowledgeRecord(agent_key="regulatory", record_type="finding", entity_key="NV-1",
        summary="Test", payload_json=json.dumps({"status": "PARTIAL", "source_url": "https://data.cms.gov/x"}), created_at=NOW))
    db.add(RecommendationKnowledgeUsageLog(agent_key="regulatory", recommendation_key="private-rec",
        resident_key="private-resident", freshness_status="FRESH", health_status="HEALTHY", decision="USED",
        policy_allowed=1, decision_reason="allowed", logged_at=NOW))
    db.commit()
    report = build_daily_report(db, NOW.date(), NOW.replace(hour=13))
    agent = next(a for a in report["agents"] if a["agent_key"] == "regulatory")
    assert agent["records_ingested"] == 1 and agent["guard_admissions"] == 1
    assert agent["engine_adopted_facts"] is None
    assert "private-rec" not in json.dumps(report) and "private-resident" not in json.dumps(report)


def test_archives_survive_repeated_capture_and_do_not_count_themselves(db):
    first = archive_daily_report(db, NOW.date(), NOW)
    archive_daily_report(db, NOW.date(), NOW.replace(hour=13))
    history = daily_report_history(db)
    assert len(history) == 2
    assert all(a["records_ingested"] == 0 for a in history[0]["agents"])
    assert history[1] == first


def test_future_window_is_rejected(db):
    with pytest.raises(ValueError):
        build_daily_report(db, date(2026, 10, 3), NOW)


def test_resolved_owner_question_is_not_repeated(db):
    for status, created in (("OPEN", NOW.replace(day=1)), ("RESOLVED", NOW)):
        db.add(AgentKnowledgeRecord(agent_key="owner_decisions", record_type="research_owner_decision_v1",
            entity_key="language", summary="Decision", payload_json=json.dumps({"status": status, "question": "Require language?"}), created_at=created))
    db.commit()
    report = build_daily_report(db, NOW.date(), NOW.replace(hour=13))
    assert report["owner_questions"] == []
    assert report["owner_decision_queue_status"] == "OBSERVED"

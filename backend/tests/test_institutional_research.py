from datetime import date, datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.agent_execution import AgentKnowledgeRecord, AgentQueueItem, AgentWorker
from app.services.research_coverage_contract import complaint_window, permitted_source, observation_status, TOPICS
from app.services.institutional_research import facility_research_report, load_observations, save_observation
from app.services.institutional_research_collectors import ResearchCollectionContext, cms_observation, collect_topic

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


@pytest.fixture
def ledger():
    engine = create_engine("sqlite:///:memory:")
    for model in (AgentKnowledgeRecord, AgentQueueItem, AgentWorker):
        model.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    with patch("app.services.institutional_research.SessionLocal", factory):
        yield factory
    engine.dispose()


def observation(status="VERIFIED", **kw):
    return {"status": status, "observed_at": NOW.isoformat(), "identity_verified": True,
            "source_url": "https://data.cms.gov/provider-data/dataset/4pq5-n9py", "data": {"overall_rating": 4}, **kw}


def test_calendar_year_window_including_leap_day():
    assert complaint_window(date(2024, 2, 29)) == (date(2023, 2, 28), date(2024, 2, 29))
    assert complaint_window(date(2025, 3, 1))[0] == date(2024, 3, 1)


@pytest.mark.parametrize("url", ["https://caring.com/x", "https://reviews.aplaceformom.com/x", "https://senioradvisor.com", "http://data.cms.gov/x", "javascript:alert(1)"])
def test_excluded_or_unsafe_sources(url):
    assert not permitted_source(url)


def test_expiry_identity_and_data_are_required():
    assert observation_status(observation(), "cms_quality", NOW) == "VERIFIED"
    assert observation_status(observation(observed_at=(NOW - timedelta(days=8)).isoformat()), "cms_quality", NOW) == "STALE"
    assert observation_status(observation(identity_verified=False), "cms_quality", NOW) == "UNKNOWN"
    assert observation_status(observation(data={}), "cms_quality", NOW) == "UNKNOWN"
    assert observation_status(observation(observed_at=(NOW + timedelta(days=1)).isoformat()), "cms_quality", NOW) == "STALE"


def test_new_failure_supersedes_old_success_and_unknown_never_means_zero(ledger):
    with ledger() as db:
        save_observation(db, "NV-1", "cms_quality", observation())
        db.commit()
        save_observation(db, "NV-1", "cms_quality", observation("SOURCE_FAILED", identity_verified=False, data={}))
        db.commit()
    records, error = load_observations(["NV-1"])
    report = facility_research_report("NV-1", {}, records["NV-1"], now=NOW)
    assert error is None
    assert report["status"] == "DEGRADED"
    assert next(t for t in report["topics"] if t["topic"] == "cms_quality")["status"] == "SOURCE_FAILED"
    complaints = next(t for t in report["topics"] if t["topic"] == "official_complaints")
    assert complaints["status"] == "NOT_CHECKED" and "complaint_count" not in complaints["data"]


def test_synthetic_pilot_is_not_real_research():
    report = facility_research_report("PILOT-NV-1", {}, {}, now=NOW)
    assert report["status"] == "SYNTHETIC_PILOT"
    with patch("app.services.institutional_research_collectors.requests.get") as get:
        assert collect_topic("PILOT-NV-1", {}, "official_complaints", ResearchCollectionContext(NOW))["status"].startswith("SYNTHETIC")
    get.assert_not_called()


def cms_context(rows):
    context = ResearchCollectionContext(NOW)
    context.provider_rows = {"295001": {"Processing Date": "2026-09-01", "Overall Rating": "4"}}
    context.deficiencies = {"295001": rows}
    return context


def test_cms_findings_are_not_complaint_count_and_dates_are_bounded():
    row = {"Complaint Deficiency": "Y", "Survey Date": "10/02/2025", "Deficiency Tag Number": "600", "Scope Severity Code": "G", "Deficiency Description": "Published finding", "Deficiency Corrected": "Y"}
    context = cms_context([row, row.copy(), {**row, "Survey Date": "10/01/2025"}, {**row, "Survey Date": "10/03/2026"}, {**row, "Survey Date": "invalid"}])
    result = cms_observation({"cms_ccn": "295001"}, "official_complaints", context)
    assert result["status"] == "PARTIAL"
    assert result["data"]["complaint_count"] is None
    assert result["data"]["published_finding_count"] == 1
    assert result["data"]["undated_complaint_related_rows"] == 1
    assert result["data"]["findings"][0]["date_type"] == "SURVEY_DATE_NOT_COMPLAINT_RECEIPT_DATE"


def test_zero_findings_does_not_establish_no_complaints():
    result = cms_observation({"cms_ccn": "295001"}, "official_complaints", cms_context([]))
    assert result["data"]["published_finding_count"] == 0
    assert result["data"]["complaint_count"] is None
    assert result["status"] == "PARTIAL"


def test_cms_failure_and_wrong_identity_cannot_be_verified():
    context = ResearchCollectionContext(NOW)
    context.cms_error = "ConnectionError"
    assert cms_observation({"cms_ccn": "295001"}, "cms_quality", context)["status"] == "SOURCE_FAILED"
    context.cms_error = None
    context.provider_rows = {}
    assert cms_observation({"cms_ccn": "295001"}, "cms_quality", context)["status"] == "IDENTITY_UNRESOLVED"


@pytest.mark.parametrize("topic", ["google_reviews", "independent_ratings", "accreditation", "staffing_operations"])
def test_unconnected_sources_are_explicit_blockers(topic):
    result = collect_topic("NV-1", {}, topic, ResearchCollectionContext(NOW))
    assert result["identity_verified"] is False
    assert result["status"] != "VERIFIED"
    assert result["data"] == {}


def test_scheduler_deduplicates_real_pending_tasks(ledger):
    from app.services.research_institute_scheduler import queue_daily_facility_refresh
    with patch("app.services.research_institute_scheduler.SessionLocal", ledger), patch("app.services.research_institute_scheduler.get_canonical_facility_index", return_value={"NV-1": {"facility_name": "Real Home"}}), patch("app.services.research_institute_scheduler._recent_completed_item", return_value=False):
        first = queue_daily_facility_refresh()
        second = queue_daily_facility_refresh(force=True)
    assert first["queued"] > len(TOPICS)
    assert second["queued"] == 0
    assert second["skipped_pending"] == first["queued"]


def test_generated_review_news_legal_and_branding_signals_are_not_collected():
    from app.services.intelligence_agent import build_facility_intelligence_profile, _build_narrative
    with patch("app.services.intelligence_agent._collect_regulatory_signals", return_value=[]), patch("app.services.intelligence_agent._collect_activation_wave3_signals") as fake, patch("app.services.intelligence_agent._collect_review_signals") as reviews, patch("app.services.intelligence_agent._build_visual_assets", return_value={}), patch("app.services.intelligence_agent._upsert_profile") as persist:
        build_facility_intelligence_profile(MagicMock(), MagicMock(medical_quality_score=0, staffing_score=50, name="Community Gardens"))
    fake.assert_not_called(); reviews.assert_not_called()
    assert persist.call_args.kwargs["signals"] == []
    assert "no major" not in persist.call_args.kwargs["narrative"]
    assert "During the last 12 months" not in _build_narrative({}, [], [], [])


def test_source_publication_age_cannot_be_reset_by_a_new_fetch():
    context = cms_context([])
    context.provider_rows["295001"]["Processing Date"] = "2025-01-01"
    assert cms_observation({"cms_ccn": "295001"}, "cms_quality", context)["status"] == "STALE"
    assert cms_observation({"cms_ccn": "295001"}, "official_complaints", context)["status"] == "STALE"


def test_report_keeps_findings_and_complaint_uncertainty_separate():
    from app.services.personal_decision_report_builder import _candidate_claims
    row = {"canonical_facility_id": "NV-1", "institutional_research": {
        "topics": [{"topic": "official_complaints", "status": "PARTIAL", "source_url": "https://data.cms.gov",
                    "limitation": "Not every complaint is published", "data": {"complaint_count": None, "findings": [
                        {"date": "2026-01-01", "subject": "Medication deficiency", "correction_status": "Y"}]}}]}}
    pairs = _candidate_claims(row)
    facts = [claim for claim, _ in pairs if claim.claim_type.value == "VERIFIED_FACT"]
    unknown = [claim for claim, _ in pairs if claim.claim_type.value == "UNKNOWN"]
    assert len(facts) == 1 and "inspection finding" in facts[0].approved_text
    assert len(unknown) == 1 and "complete record" in unknown[0].approved_text
    row["institutional_research"]["topics"][0]["status"] = "STALE"
    assert not [claim for claim, _ in _candidate_claims(row) if claim.claim_type.value == "VERIFIED_FACT"]


def test_nevada_login_and_unconfirmed_page_never_mean_no_complaints():
    from app.services.institutional_research_collectors import nevada_observation
    url = "https://nvdpbh.aithent.com/Protected/INS/SODPublicView.aspx?LicenseNumber=10013"
    response = MagicMock(url="https://nvdpbh.aithent.com/login.aspx", content=b"Login", text="Login")
    with patch("app.services.decision_engine_evidence._regulatory_index", return_value={"NV-1": {"source_url": url}}), patch("app.services.institutional_research_collectors.requests.get", return_value=response):
        result = nevada_observation("NV-1", {}, "official_complaints", ResearchCollectionContext(NOW))
    assert result["status"] == "ACCESS_BLOCKED"
    assert "complaint_count" not in result["data"]


def test_cms_collects_once_per_batch():
    rows = [{"State": "NV", "CMS Certification Number (CCN)": "295001", "Processing Date": "2026-09-01"}]
    context = ResearchCollectionContext(NOW)
    with patch("app.services.institutional_research_collectors._cms_rows", return_value=iter(rows)) as read:
        context.providers()
        context.providers()
    assert read.call_count == 1


def test_known_findings_survive_failed_refresh_without_claiming_current_coverage(ledger):
    with ledger() as db:
        save_observation(db, "NV-1", "official_complaints", observation("PARTIAL", data={
            "findings": [{"date": "2026-01-01", "tag": "600", "subject": "Known finding"}]}))
        db.commit()
        save_observation(db, "NV-1", "official_complaints", observation("SOURCE_FAILED", data={}, identity_verified=False))
        db.commit()
    records, _ = load_observations(["NV-1"])
    report = facility_research_report("NV-1", {}, records["NV-1"], now=NOW)
    topic = next(t for t in report["topics"] if t["topic"] == "official_complaints")
    assert topic["status"] == "SOURCE_FAILED"
    assert topic["known_findings"][0]["subject"] == "Known finding"
    assert report["status"] == "DEGRADED"
    later = facility_research_report("NV-1", {}, records["NV-1"], now=NOW + timedelta(days=365))
    assert next(t for t in later["topics"] if t["topic"] == "official_complaints")["known_findings"] == []

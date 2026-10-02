from unittest.mock import MagicMock, patch
from app.services.decision_agent_bridge import _queue

def test_synthetic_pilot_is_never_queued_for_public_web_research():
    db=MagicMock()
    assert _queue(db,{"canonical_facility_id":"PILOT-NV-001","synthetic_pilot":True},"care_support",["adl_support"]) is False
    db.add.assert_not_called()

def test_daily_scheduler_skips_synthetic_and_queues_real_catalog():
    fake_db=MagicMock()
    fake_db.query.return_value.filter.return_value.all.return_value=[]
    with patch("app.services.research_institute_scheduler.SessionLocal",return_value=fake_db), patch(
        "app.services.research_institute_scheduler.get_canonical_facility_index",
        return_value={"PILOT-NV-001":{"synthetic_pilot":True},"NV-REAL-1":{"facility_name":"Real Home","city":"LAS VEGAS"}},
    ), patch("app.services.research_institute_scheduler._recent_completed_item",return_value=False), patch(
        "app.services.research_institute_scheduler._ensure_worker"
    ):
        from app.services.research_institute_scheduler import queue_daily_facility_refresh
        result=queue_daily_facility_refresh()
    assert result["synthetic_skipped"]==1
    assert result["queued"]>0

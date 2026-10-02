from app.services.research_institute_scheduler import queue_event_refresh
from unittest.mock import patch

def test_event_refresh_never_researches_synthetic_pilot():
    assert queue_event_refresh(canonical_facility_id="PILOT-NV-001",reason="page changed")["status"]=="SKIPPED_SYNTHETIC"

def test_event_refresh_queues_room_pricing_for_real_facility():
    class DB:
        def add(self,x): pass
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass
    with patch("app.services.research_institute_scheduler.SessionLocal",return_value=DB()), patch(
        "app.services.research_institute_scheduler.get_canonical_facility_index",
        return_value={"NV-1":{"facility_name":"Real Home","city":"LAS VEGAS"}},
    ), patch("app.services.research_institute_scheduler._ensure_worker"), patch("app.services.research_institute_scheduler._active_tasks", return_value=set()):
        result=queue_event_refresh(canonical_facility_id="NV-1",reason="official page changed")
    assert result["queued"]==2

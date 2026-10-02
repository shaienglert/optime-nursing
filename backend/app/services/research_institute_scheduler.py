from __future__ import annotations

"""Research Institute scheduler: refresh real facility evidence independently of family searches."""
import json
from datetime import datetime, timezone
from typing import Any, Dict

from app.database import SessionLocal
from app.models.agent_execution import AgentQueueItem
from app.services.decision_agent_bridge import QUEUE_TYPE, _ensure_worker, _recent_completed_item
from app.services.facility_parameter_service import get_canonical_facility_index
from app.services.research_coverage_contract import TOPICS

DAILY_DIMENSIONS={
    "provider_intelligence": ("care_support","social_engagement","rehab_path","couple_coresidence","recovery_transition","room_pricing"),
    "regulatory_intelligence": ("facility_quality_safety", *TOPICS),
}


def _active_tasks(db) -> set[tuple[str, str]]:
    active = set()
    items = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE,
                                           AgentQueueItem.status.in_(["PENDING", "RUNNING"])).all()
    for item in items:
        try:
            payload = json.loads(item.payload_json or "{}")
            active.add((str(payload.get("canonical_facility_id") or ""), str(payload.get("dimension") or "")))
        except (TypeError, ValueError):
            continue
    return active

def queue_daily_facility_refresh(*, force:bool=False)->Dict[str,Any]:
    db=SessionLocal(); queued=skipped=synthetic=pending=0
    try:
        active = _active_tasks(db)
        for cid,row in get_canonical_facility_index().items():
            if row.get("synthetic_pilot") is True or str(cid).startswith("PILOT-NV-"):
                synthetic+=1; continue
            for agent_key,dimensions in DAILY_DIMENSIONS.items():
                _ensure_worker(db,agent_key)
                for dimension in dimensions:
                    if (str(cid), dimension) in active:
                        pending += 1; continue
                    if not force and _recent_completed_item(db,str(cid),dimension,24):
                        skipped+=1; continue
                    payload={"market":"las-vegas","canonical_facility_id":str(cid),"facility_name":row.get("facility_name") or row.get("name"),"city":row.get("city") or "LAS VEGAS","state":"NV","dimension":dimension,"requested_parameters":[],"requested_at":datetime.now(timezone.utc).isoformat(),"research_trigger":"DAILY_RESEARCH_INSTITUTE"}
                    db.add(AgentQueueItem(queue_type=QUEUE_TYPE,agent_key=agent_key,payload_json=json.dumps(payload,sort_keys=True),status="PENDING",max_attempts=3)); queued+=1
                    active.add((str(cid), dimension))
        db.commit()
        return {"status":"QUEUED","queued":queued,"skipped_recent":skipped,"skipped_pending":pending,"synthetic_skipped":synthetic}
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


def queue_event_refresh(*, canonical_facility_id:str, reason:str, dimensions:tuple[str,...]=("care_support","room_pricing"))->Dict[str,Any]:
    """Queue an immediate refresh after a detected source/provider/regulatory change."""
    if str(canonical_facility_id).startswith("PILOT-NV-"):
        return {"status":"SKIPPED_SYNTHETIC","queued":0}
    index=get_canonical_facility_index()
    row=index.get(canonical_facility_id) or {}
    if not row:
        return {"status":"UNKNOWN_FACILITY","queued":0}
    if row.get("synthetic_pilot") is True:
        return {"status":"SKIPPED_SYNTHETIC","queued":0}
    db=SessionLocal(); queued=0
    try:
        active = _active_tasks(db)
        for dimension in dimensions:
            if (canonical_facility_id, dimension) in active:
                continue
            agent_key="regulatory_intelligence" if dimension=="facility_quality_safety" or dimension in TOPICS else "provider_intelligence"
            _ensure_worker(db,agent_key)
            payload={"market":"las-vegas","canonical_facility_id":canonical_facility_id,"facility_name":row.get("facility_name") or row.get("name"),"city":row.get("city") or "LAS VEGAS","state":"NV","dimension":dimension,"requested_parameters":[],"requested_at":datetime.now(timezone.utc).isoformat(),"research_trigger":"EVENT_DRIVEN_REFRESH","refresh_reason":reason}
            db.add(AgentQueueItem(queue_type=QUEUE_TYPE,agent_key=agent_key,payload_json=json.dumps(payload,sort_keys=True),status="PENDING",max_attempts=3)); queued+=1
            active.add((canonical_facility_id, dimension))
        db.commit()
        return {"status":"QUEUED","queued":queued,"reason":reason}
    except Exception:
        db.rollback(); raise
    finally:
        db.close()

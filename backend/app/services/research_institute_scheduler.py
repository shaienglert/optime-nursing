from __future__ import annotations

"""Research Institute scheduler: refresh real facility evidence independently of family searches."""
import json
from datetime import datetime, timezone
from typing import Any, Dict

from app.database import SessionLocal
from app.models.agent_execution import AgentQueueItem
from app.services.decision_agent_bridge import QUEUE_TYPE, _ensure_worker, _recent_completed_item
from app.services.facility_parameter_service import get_canonical_facility_index

DAILY_DIMENSIONS={
    "provider_intelligence": ("care_support","social_engagement","rehab_path","couple_coresidence","recovery_transition"),
    "regulatory_intelligence": ("facility_quality_safety",),
}

def queue_daily_facility_refresh(*, force:bool=False)->Dict[str,Any]:
    db=SessionLocal(); queued=skipped=synthetic=0
    try:
        for cid,row in get_canonical_facility_index().items():
            if row.get("synthetic_pilot") is True or str(cid).startswith("PILOT-NV-"):
                synthetic+=1; continue
            for agent_key,dimensions in DAILY_DIMENSIONS.items():
                _ensure_worker(db,agent_key)
                for dimension in dimensions:
                    if not force and _recent_completed_item(db,str(cid),dimension,24):
                        skipped+=1; continue
                    payload={"market":"las-vegas","canonical_facility_id":str(cid),"facility_name":row.get("facility_name") or row.get("name"),"city":row.get("city") or "LAS VEGAS","state":"NV","dimension":dimension,"requested_parameters":[],"requested_at":datetime.now(timezone.utc).isoformat(),"research_trigger":"DAILY_RESEARCH_INSTITUTE"}
                    db.add(AgentQueueItem(queue_type=QUEUE_TYPE,agent_key=agent_key,payload_json=json.dumps(payload,sort_keys=True),status="PENDING",max_attempts=3)); queued+=1
        db.commit()
        return {"status":"QUEUED","queued":queued,"skipped_recent":skipped,"synthetic_skipped":synthetic}
    except Exception:
        db.rollback(); raise
    finally:
        db.close()

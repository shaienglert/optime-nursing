"""Hard market boundary for the Nevada-only public product.

Legacy Florida CMS rows must never coexist with the Nevada launch dataset: their
presence makes old numeric facility routes capable of displaying the wrong market.
This cleanup is intentionally destructive for every non-Nevada facility and its
facility-specific evidence.  It is idempotent and runs before startup decides
whether a Nevada import is required.
"""

from __future__ import annotations

from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.agent_execution import RecommendationAgentVersionTrace
from app.models.clinical_evidence import RecommendationEvidenceLink
from app.models.external_discovery import ExternalSourceRequestLog
from app.models.facility import Facility, ResidentOutcome


NEVADA_STATE_CODE = "NV"


def purge_non_nevada_facilities(db: Session) -> Dict[str, int]:
    """Delete all facility rows outside Nevada and their facility-specific traces."""
    facilities = (
        db.query(Facility)
        .filter(func.upper(func.trim(Facility.state)) != NEVADA_STATE_CODE)
        .order_by(Facility.id.asc())
        .all()
    )
    facility_ids = [int(facility.id) for facility in facilities]
    if not facility_ids:
        return {"facilities_deleted": 0, "evidence_links_deleted": 0, "discovery_logs_deleted": 0, "outcomes_detached": 0, "traces_detached": 0}

    evidence_links_deleted = (
        db.query(RecommendationEvidenceLink)
        .filter(RecommendationEvidenceLink.facility_id.in_(facility_ids))
        .delete(synchronize_session=False)
    )
    discovery_logs_deleted = (
        db.query(ExternalSourceRequestLog)
        .filter(ExternalSourceRequestLog.facility_id.in_(facility_ids))
        .delete(synchronize_session=False)
    )
    outcomes_detached = (
        db.query(ResidentOutcome)
        .filter(ResidentOutcome.facility_id.in_(facility_ids))
        .update({ResidentOutcome.facility_id: None}, synchronize_session=False)
    )
    traces_detached = (
        db.query(RecommendationAgentVersionTrace)
        .filter(RecommendationAgentVersionTrace.facility_id.in_(facility_ids))
        .update({RecommendationAgentVersionTrace.facility_id: None}, synchronize_session=False)
    )
    for facility in facilities:
        db.delete(facility)
    db.commit()
    return {
        "facilities_deleted": len(facility_ids),
        "evidence_links_deleted": int(evidence_links_deleted or 0),
        "discovery_logs_deleted": int(discovery_logs_deleted or 0),
        "outcomes_detached": int(outcomes_detached or 0),
        "traces_detached": int(traces_detached or 0),
    }

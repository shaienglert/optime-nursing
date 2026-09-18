from __future__ import annotations

"""Seed synthetic "verified" evidence for the fictional pilot market.

governed_evidence_runtime.py's published_rates_verified flag can only ever be
set from a real research agent's AgentKnowledgeRecord, or from the static
real-Nevada provider_housing_primary_evidence.json overlay (which itself
excludes SKILLED_NURSING-type facilities -- see get_provider_housing_evidence
in provider_housing_runtime.py). Neither path can ever fire for the 200
fictional pilot facilities: there is no real facility to research or verify.
That left every pilot recommendation permanently stuck at
MUST_PENDING_VERIFICATION for budget, no matter how complete the rest of the
pilot's synthetic data was. This seeds one clearly-labeled synthetic
AgentKnowledgeRecord per pilot facility so the pilot can demonstrate a final,
not just provisional, recommendation. Only ever runs for
OPTIME_CANONICAL_MARKET=synthetic-pilot, and only ever touches pilot
canonical ids, so it can never affect a real Nevada/Florida facility.
"""

import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.agent_execution import AgentKnowledgeRecord
from app.services.canonical_universe import configured_canonical_market
from app.services.facility_parameter_service import get_all_canonical_facility_ids

SEED_AGENT_KEY = "synthetic_pilot_published_rates_seed"
SEED_SOURCE = "SYNTHETIC_PILOT_DEMO_EVIDENCE"


def seed_synthetic_pilot_published_rates_evidence(db: Session) -> Dict[str, Any]:
    if configured_canonical_market() != "synthetic-pilot":
        return {"status": "SKIPPED_NOT_PILOT_MARKET"}

    canonical_ids = [cid for cid in get_all_canonical_facility_ids() if cid]
    if not canonical_ids:
        return {"status": "NO_PILOT_FACILITIES_FOUND", "newly_seeded": 0}

    already_seeded = {
        row[0]
        for row in db.query(AgentKnowledgeRecord.entity_key)
        .filter(AgentKnowledgeRecord.agent_key == SEED_AGENT_KEY)
        .all()
    }
    missing = [cid for cid in canonical_ids if cid not in already_seeded]
    for canonical_id in missing:
        payload = {
            "market": "las vegas",
            "published_rates_verified": True,
            "synthetic_pilot": True,
            "not_real_world_evidence": True,
        }
        db.add(AgentKnowledgeRecord(
            agent_key=SEED_AGENT_KEY,
            record_type="PILOT_PUBLISHED_RATES_VERIFICATION",
            entity_key=canonical_id,
            summary=(
                "Synthetic pilot demo evidence: published rates presumed verified "
                "for demonstration purposes only. Not a real verification."
            ),
            payload_json=json.dumps(payload, sort_keys=True),
            confidence=1.0,
            source=SEED_SOURCE,
        ))
    if missing:
        db.commit()
    return {
        "status": "OK",
        "pilot_facility_count": len(canonical_ids),
        "already_seeded": len(already_seeded),
        "newly_seeded": len(missing),
    }


__all__ = ["seed_synthetic_pilot_published_rates_evidence"]

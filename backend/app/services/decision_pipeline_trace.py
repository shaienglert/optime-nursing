from __future__ import annotations

"""One observable outcome contract for the governed recommendation pipeline.

The trace records why a request has no visible recommendation without letting a later
visibility step erase the earlier MUST/ranking outcome.  It is intentionally derived
from the canonical payload, so it cannot become a second decision authority.
"""

from collections import Counter
from typing import Any, Dict


def attach_decision_pipeline_trace(result: Dict[str, Any]) -> Dict[str, Any]:
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    pipeline = decision.get("facility_selection_pipeline") if isinstance(decision.get("facility_selection_pipeline"), dict) else {}
    canonical = decision.get("canonical_decision_state") if isinstance(decision.get("canonical_decision_state"), dict) else {}
    dispositions = pipeline.get("candidate_dispositions") if isinstance(pipeline.get("candidate_dispositions"), list) else []
    reason_counts = Counter(
        str(row.get("reason_code") or "UNKNOWN")
        for row in dispositions
        if isinstance(row, dict)
    )
    visible = len(result.get("results") or [])
    trace = {
        "version": "decision-pipeline-trace-v1",
        "candidate_counts": {
            "total_scored": int(result.get("total_candidates_scored") or len(dispositions)),
            "must_eligible": int(result.get("must_eligible_count") or 0),
            "must_pending_verification": int(result.get("must_pending_verification_count") or 0),
            "must_rejected": int(result.get("must_rejected_count") or 0),
            "visible_recommendations": visible,
        },
        "gates": {
            "must": {"status": canonical.get("must"), "reason_counts": dict(sorted(reason_counts.items()))},
            "ai_ranking": dict(pipeline.get("ai_ranking") or {}),
            "visibility": {
                "allowed": decision.get("recommendation_execution_allowed") is True,
                "phase": canonical.get("phase"),
                "reason": canonical.get("reason"),
                "next_action": canonical.get("next_action"),
            },
        },
        "outcome": "VISIBLE_RECOMMENDATIONS" if visible else "NO_VISIBLE_RECOMMENDATIONS",
        "contract": "A candidate with unresolved (not failed) MUST evidence is ranked and shown alongside MUST-eligible candidates on today's evidence, with an explicit per-candidate note of what remains unverified; only an explicit MUST failure excludes a candidate from the shortlist.",
    }
    result["decision_pipeline_trace"] = trace
    audit = result.get("recommendation_audit_trace") if isinstance(result.get("recommendation_audit_trace"), dict) else {}
    audit["decision_pipeline_trace"] = trace
    result["recommendation_audit_trace"] = audit
    return result


__all__ = ["attach_decision_pipeline_trace"]

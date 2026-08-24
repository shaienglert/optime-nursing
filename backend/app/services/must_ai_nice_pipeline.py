from __future__ import annotations

"""Final facility selection pipeline.

1. Deterministic MUST gate, no AI discretion.
2. Semantic AI ranking only among facilities with hard_gate=PASS.
3. Deterministic NICE coverage reporting.
4. PENDING MUST candidates remain research candidates, never recommendations.
5. Final facility facts can be verified and the same eligible set re-ranked later.
"""

from typing import Any, Dict, List

from app.services.ai_candidate_ranking_runtime import attach_nice_coverage, rank_must_eligible_candidates
from app.services.client_intent_runtime import intent_rank_key


def _fallback_key(row: Dict[str, Any]) -> tuple[Any, ...]:
    return intent_rank_key(row)


def apply_must_ai_nice_pipeline(
    result: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
    limit: int,
) -> Dict[str, Any]:
    rows = list(result.get("results") or [])
    decision = result.setdefault("decision_intelligence", {})
    client_intent = decision.get("client_intent") if isinstance(decision.get("client_intent"), dict) else {}
    human_context = decision.get("human_intelligence") if isinstance(decision.get("human_intelligence"), dict) else {}
    strategy = decision.get("living_strategy") if isinstance(decision.get("living_strategy"), dict) else {}

    eligible: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for row in rows:
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        gate = str(fit.get("hard_gate") or "PENDING_VERIFICATION").upper()
        if gate == "PASS":
            row["must_eligibility"] = "MUST_ELIGIBLE"
            eligible.append(row)
        elif gate == "FAIL":
            row["must_eligibility"] = "MUST_REJECTED"
            rejected.append(row)
        else:
            row["must_eligibility"] = "MUST_PENDING_VERIFICATION"
            pending.append(row)

    ranked, ai_status = rank_must_eligible_candidates(
        eligible,
        client_intent=client_intent,
        human_context=human_context,
        strategy=strategy,
        deterministic_fallback_key=_fallback_key,
    )
    nice_summary = attach_nice_coverage(ranked, client_intent)

    for position, row in enumerate(ranked, start=1):
        row["rank_position"] = position
        row["rank_display"] = f"#{position}"
        row["rank_tie_status"] = "UNIQUE_RANK"
        row["tied_with"] = []
        row.setdefault("explanation", {})["selection_pipeline"] = {
            "stage_1": "MUST_ELIGIBLE_DETERMINISTIC",
            "stage_2": ai_status.get("status"),
            "stage_3": (row.get("nice_to_have_coverage") or {}).get("status"),
            "unknown_policy": "UNKNOWN_IS_INFORMATION_DEFICIT_NOT_NEGATIVE_EVIDENCE",
        }

    selected = ranked[: max(0, int(limit or 0))]
    complete_selected = [row for row in selected if (row.get("nice_to_have_coverage") or {}).get("status") == "NICE_COMPLETE"]

    result["results"] = selected
    result["result_count"] = len(selected)
    result["must_eligible_count"] = len(eligible)
    result["must_pending_verification_count"] = len(pending)
    result["must_rejected_count"] = len(rejected)
    result["must_pending_verification_candidates"] = [
        {
            "canonical_facility_id": row.get("canonical_facility_id"),
            "facility_name": row.get("facility_name"),
            "must_unknown": (row.get("client_intent_fit") or {}).get("must_unknown") or [],
        }
        for row in pending
    ]

    decision["facility_selection_pipeline"] = {
        "version": "must-ai-nice-v1",
        "order": [
            "DETERMINISTIC_MUST_GATE",
            "SEMANTIC_AI_RANK_MUST_ELIGIBLE",
            "DETERMINISTIC_NICE_COVERAGE",
            "PROVIDER_FACT_VERIFICATION",
            "AI_RERANK_AFTER_NEW_EVIDENCE",
        ],
        "must_eligible_count": len(eligible),
        "must_pending_verification_count": len(pending),
        "must_rejected_count": len(rejected),
        "ai_ranking": ai_status,
        "nice_to_have": nice_summary,
        "top_nice_complete_count": len(complete_selected),
        "top_nice_complete_candidate_ids": [str(row.get("canonical_facility_id")) for row in complete_selected],
        "client_statement": (
            f"We currently have {len(complete_selected)} top-ranked facilities that pass every MUST requirement and match every verified NICE-TO-HAVE. "
            "This is the current ranking based on the evidence available now. We recommend verifying the remaining provider-specific facts directly with the facilities; those answers may change the ranking and make the recommendation more precise."
            if complete_selected
            else
            "The displayed facilities pass every verified MUST requirement. Some NICE-TO-HAVE evidence is still incomplete, so this ranking is provisional and provider verification can materially improve it."
        ),
        "rule": "AI never decides MUST eligibility. Only MUST_ELIGIBLE facilities are ranked for the client; MUST_PENDING_VERIFICATION stays in research and can enter a later rerank only after verification.",
    }
    decision["must_gate"] = {
        **(decision.get("must_gate") if isinstance(decision.get("must_gate"), dict) else {}),
        "eligible": len(eligible),
        "pending_verification": len(pending),
        "rejected": len(rejected),
        "selected_must_unknown_count": 0,
    }
    decision["ranking_order"] = [
        "DETERMINISTIC_MUST_GATE",
        "SEMANTIC_AI_ALL_GOVERNED_EVIDENCE",
        "NICE_COVERAGE_DISCLOSURE",
        "PROVIDER_VERIFICATION",
        "AI_RERANK",
    ]
    decision["recommendation_visibility"] = "PROVISIONAL_RANKING_VISIBLE" if selected else "NO_MUST_ELIGIBLE_RESULTS"
    decision["recommendation_execution_allowed"] = bool(selected)
    if selected:
        decision["decision_finality"] = "PROVISIONAL_PENDING_PROVIDER_VERIFICATION"
    result["decision_intelligence"] = decision
    return result


__all__ = ["apply_must_ai_nice_pipeline"]

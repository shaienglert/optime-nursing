from __future__ import annotations

"""Final facility selection pipeline.

1. Deterministic MUST gate, no AI discretion.
2. Semantic AI owns an open-ended preference model and ranks only MUST_ELIGIBLE rows.
3. Dynamic preference verification is evidence-closed-world: MATCH/MISMATCH requires
   governed claims; missing evidence stays UNKNOWN.
4. Legacy structured NICE signals are audit-only and cannot drive the authoritative
   ranking or NICE_COMPLETE result.
5. PENDING MUST candidates remain research candidates, never recommendations.
6. Provider verification can add governed claims and trigger an AI rerank later.
7. When AI candidate ranking is explicitly required, an unavailable AI ranking fails
   closed: deterministic ordering may remain in diagnostics but is never exposed as a
   recommendation.
"""

from copy import deepcopy
import os
from typing import Any, Dict, List

from app.services.ai_candidate_ranking_runtime import attach_nice_coverage, rank_must_eligible_candidates
from app.services.client_intent_runtime import intent_rank_key
from app.services.human_intelligence_runtime_verified import person_fit_sort_key
from app.services.semantic_preference_runtime import build_dynamic_preference_model, verify_dynamic_preferences


def _fallback_key(row: Dict[str, Any]) -> tuple[Any, ...]:
    return (*person_fit_sort_key(row), *intent_rank_key(row))


def _remove_legacy_nice_from_authoritative_path(rows: List[Dict[str, Any]]) -> None:
    for row in rows:
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        row["legacy_structured_nice_fit"] = {
            "nice_match": list(fit.get("nice_match") or []),
            "nice_unknown": list(fit.get("nice_unknown") or []),
            "nice_fit_scores": dict(fit.get("nice_fit_scores") or {}),
        }
        fit["nice_match"] = []
        fit["nice_unknown"] = []
        fit["nice_fit_scores"] = {}


def _env_true(name: str) -> bool:
    return os.getenv(name, "0").strip().lower() in {"1", "true", "yes", "on"}


def _ai_ranking_succeeded(ai_status: Dict[str, Any]) -> bool:
    return str(ai_status.get("status") or "").upper() in {"AI_RANKED", "AI_BATCH_RANKED"}


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

    dynamic_preferences = build_dynamic_preference_model(human_context)
    human_context["dynamic_preference_model"] = dynamic_preferences
    decision["dynamic_preference_model"] = dynamic_preferences

    audit_intent = deepcopy(client_intent)
    _remove_legacy_nice_from_authoritative_path(eligible)
    ranking_intent = deepcopy(client_intent)
    ranking_intent["nice_to_haves"] = []

    ranked, ai_status = rank_must_eligible_candidates(
        eligible,
        client_intent=ranking_intent,
        human_context=human_context,
        strategy=strategy,
        deterministic_fallback_key=_fallback_key,
    )

    ai_failure_block = (
        bool(eligible)
        and _env_true("OPTIME_SEMANTIC_AI_ENABLED")
        and _env_true("OPTIME_AI_CANDIDATE_RANKING_REQUIRED")
        and not _ai_ranking_succeeded(ai_status)
    )

    audit_rows = deepcopy(ranked)
    for audit_row in audit_rows:
        legacy = audit_row.get("legacy_structured_nice_fit") if isinstance(audit_row.get("legacy_structured_nice_fit"), dict) else {}
        fit = audit_row.get("client_intent_fit") if isinstance(audit_row.get("client_intent_fit"), dict) else {}
        fit["nice_match"] = list(legacy.get("nice_match") or [])
        fit["nice_unknown"] = list(legacy.get("nice_unknown") or [])
        fit["nice_fit_scores"] = dict(legacy.get("nice_fit_scores") or {})
    structured_nice_summary = attach_nice_coverage(audit_rows, audit_intent)

    selected = [] if ai_failure_block else ranked[: max(0, int(limit or 0))]
    dynamic_summary = verify_dynamic_preferences(selected, dynamic_preferences)

    if not dynamic_preferences.get("preference_count"):
        for row in selected:
            row["nice_to_have_coverage"] = {
                "status": "NO_EXPLICIT_DYNAMIC_NICE",
                "required": [],
                "verified_match": [],
                "unresolved": [],
                "verified_match_count": 0,
                "required_count": 0,
                "source": "DYNAMIC_SEMANTIC_PREFERENCE_MODEL",
            }

    for position, row in enumerate(ranked, start=1):
        row["rank_position"] = position
        row["rank_display"] = f"#{position}"
        row["rank_tie_status"] = "UNIQUE_RANK"
        row["tied_with"] = []
        row.setdefault("explanation", {})["selection_pipeline"] = {
            "stage_1": "MUST_ELIGIBLE_DETERMINISTIC",
            "stage_2": ai_status.get("status"),
            "stage_3": "DYNAMIC_SEMANTIC_PREFERENCE_EVIDENCE",
            "unknown_policy": "UNKNOWN_IS_INFORMATION_DEFICIT_NOT_NEGATIVE_EVIDENCE",
            "legacy_nice_role": "AUDIT_ONLY",
        }

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

    preference_count = int(dynamic_preferences.get("preference_count") or 0)
    decision["facility_selection_pipeline"] = {
        "version": "must-ai-dynamic-preferences-v4",
        "order": [
            "DETERMINISTIC_MUST_GATE",
            "SEMANTIC_AI_DYNAMIC_PREFERENCE_MODEL",
            "SEMANTIC_AI_RANK_MUST_ELIGIBLE",
            "EVIDENCE_CLOSED_WORLD_PREFERENCE_VERIFICATION",
            "PROVIDER_FACT_VERIFICATION",
            "AI_RERANK_AFTER_NEW_EVIDENCE",
        ],
        "must_eligible_count": len(eligible),
        "must_pending_verification_count": len(pending),
        "must_rejected_count": len(rejected),
        "ai_ranking": ai_status,
        "ai_ranking_required": _env_true("OPTIME_AI_CANDIDATE_RANKING_REQUIRED"),
        "ai_ranking_fail_closed": ai_failure_block,
        "dynamic_preferences": dynamic_summary,
        "legacy_structured_nice_audit": structured_nice_summary,
        "legacy_structured_nice_authoritative": False,
        "top_nice_complete_count": len(complete_selected),
        "top_nice_complete_candidate_ids": [str(row.get("canonical_facility_id")) for row in complete_selected],
        "client_statement": (
            "We cannot present a recommendation yet because the required AI ranking did not complete successfully. The deterministic candidate order is retained only for diagnostics and is not exposed as a recommendation."
            if ai_failure_block
            else (
                f"We currently have {len(complete_selected)} top-ranked facilities that pass every MUST requirement and have governed evidence matching every specific preference you expressed. This ranking can still change when we verify missing provider facts directly with the facilities."
                if preference_count and complete_selected
                else (
                    "The displayed facilities pass every verified MUST requirement. Some of your specific preferences are still unverified, so this ranking is provisional and direct provider verification can materially improve it."
                    if preference_count
                    else "The displayed facilities pass every verified MUST requirement. No explicit NICE preference-completeness claim is being made; provider verification can still improve the ranking."
                )
            )
        ),
        "rule": "AI never decides MUST eligibility. When candidate AI ranking is required, failed ranking cannot silently degrade into a user-visible deterministic recommendation. MATCH/MISMATCH requires governed facility claims; otherwise the preference remains UNKNOWN.",
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
        "SEMANTIC_AI_DYNAMIC_PREFERENCES",
        "SEMANTIC_AI_ALL_GOVERNED_EVIDENCE",
        "EVIDENCE_GROUNDED_PREFERENCE_COVERAGE",
        "PROVIDER_VERIFICATION",
        "AI_RERANK",
    ]

    if ai_failure_block:
        decision["recommendation_visibility"] = "BLOCKED_AI_RANKING_UNAVAILABLE"
        decision["recommendation_execution_allowed"] = False
        decision["decision_finality"] = "BLOCKED_AI_RANKING_UNAVAILABLE"
        decision["ai_ranking_failure"] = {
            "status": ai_status.get("status"),
            "candidate_count": len(eligible),
            "deterministic_order_exposed": False,
            "rule": "AI-owned ranking failure must fail closed rather than masquerade as an AI recommendation.",
        }
    else:
        decision["recommendation_visibility"] = "PROVISIONAL_RANKING_VISIBLE" if selected else "NO_MUST_ELIGIBLE_RESULTS"
        decision["recommendation_execution_allowed"] = bool(selected)
        if selected:
            decision["decision_finality"] = "PROVISIONAL_PENDING_PROVIDER_VERIFICATION"

    result["decision_intelligence"] = decision
    return result


__all__ = ["apply_must_ai_nice_pipeline"]

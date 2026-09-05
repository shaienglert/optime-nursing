from __future__ import annotations

"""Final facility selection pipeline.

1. Deterministic MUST gate, no AI discretion.
2. Semantic AI owns an open-ended preference model and ranks only MUST_ELIGIBLE rows.
3. Dynamic preference verification is evidence-closed-world: MATCH/MISMATCH requires
   governed claims; missing evidence stays UNKNOWN.
4. Legacy structured NICE signals are audit-only and cannot drive the authoritative
   ranking or NICE_COMPLETE result.
5. A MUST criterion with no evidence yet is a research item, not a rejection: a
   PENDING candidate is ranked alongside MUST_ELIGIBLE ones on whatever evidence
   already exists, and shown with an explicit note of what is still unverified.
   Missing evidence is scored as neutral, never as a negative -- so confirming it
   later can only hold or improve the candidate's rank, never worsen it. Only an
   explicit MUST_FAIL (governed evidence contradicts a requirement) is excluded.
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


def _resolve_nice_wave_search_cap() -> int:
    return max(10, min(200, int(os.getenv("OPTIME_NICE_WAVE_SEARCH_MAX_CANDIDATES", "40"))))


def _verify_dynamic_preferences_in_waves(
    ranked: List[Dict[str, Any]],
    dynamic_preferences: Dict[str, Any],
    target_complete_count: int,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Verify NICE preferences past the displayed top-N in ranked waves.

    A candidate ranked just outside the display window can still be NICE_COMPLETE.
    Only checking ranked[:limit] means the pipeline would never discover it. This
    searches rank 1..N, then N+1..2N, etc. until enough NICE_COMPLETE candidates are
    found, the ranked list is exhausted, or the search cap is hit (bounded so a
    preference nobody matches doesn't trigger AI verification of every eligible
    facility).
    """
    if not dynamic_preferences.get("preference_count") or target_complete_count <= 0:
        return verify_dynamic_preferences([], dynamic_preferences), []

    wave_size = target_complete_count
    search_limit = min(len(ranked), _resolve_nice_wave_search_cap())
    complete_rows: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {}
    verified_count = 0
    start = 0

    while start < search_limit and len(complete_rows) < target_complete_count:
        wave = ranked[start:min(start + wave_size, search_limit)]
        if not wave:
            break
        wave_summary = verify_dynamic_preferences(wave, dynamic_preferences)
        verified_count += len(wave)
        complete_rows.extend(
            row for row in wave if (row.get("nice_to_have_coverage") or {}).get("status") == "NICE_COMPLETE"
        )
        summary = {
            **wave_summary,
            "nice_complete_candidate_count": len(complete_rows),
            "candidates_verified": verified_count,
            "waves_searched": (start // wave_size) + 1,
        }
        start += wave_size
        if wave_summary.get("status") != "VERIFIED":
            # AI unavailable/disabled: every further wave is an identical
            # placeholder pass, so searching deeper cannot find more matches.
            break

    return summary, complete_rows


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
            row["must_disposition_reason"] = "MUST_PASS"
            eligible.append(row)
        elif gate == "FAIL":
            row["must_eligibility"] = "MUST_REJECTED"
            row["must_disposition_reason"] = "MUST_FAIL"
            rejected.append(row)
        else:
            row["must_eligibility"] = "MUST_PENDING_VERIFICATION"
            row["must_disposition_reason"] = "MUST_EVIDENCE_PENDING"
            pending.append(row)

    dynamic_preferences = build_dynamic_preference_model(human_context)
    human_context["dynamic_preference_model"] = dynamic_preferences
    decision["dynamic_preference_model"] = dynamic_preferences

    # Pending candidates are ranked together with eligible ones: a MUST item with no
    # evidence yet is not a veto, so it must not silently disappear from the shortlist.
    rankable = eligible + pending

    audit_intent = deepcopy(client_intent)
    _remove_legacy_nice_from_authoritative_path(rankable)
    ranking_intent = deepcopy(client_intent)
    ranking_intent["nice_to_haves"] = []

    ranked, ai_status = rank_must_eligible_candidates(
        rankable,
        client_intent=ranking_intent,
        human_context=human_context,
        strategy=strategy,
        deterministic_fallback_key=_fallback_key,
    )

    ai_failure_block = (
        bool(rankable)
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
    dynamic_summary, nice_complete_rows = _verify_dynamic_preferences_in_waves(
        [] if ai_failure_block else ranked, dynamic_preferences, max(0, int(limit or 0))
    )

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
        if row.get("must_eligibility") == "MUST_PENDING_VERIFICATION":
            still_unverified = list((row.get("client_intent_fit") or {}).get("must_unknown") or [])
            row["provisional_ranking_note"] = {
                "status": "MUST_VERIFICATION_PENDING",
                "still_unverified": still_unverified,
                "statement": (
                    (
                        "This is not yet a confirmed match: "
                        + ", ".join(still_unverified)
                        + " still need to be verified for this facility. Ranked here using only "
                        "the evidence already available; unverified items are not held against it. "
                        "If they are confirmed, this facility's rank can only stay the same or improve, "
                        "never get worse."
                    )
                    if still_unverified
                    else (
                        "This is not yet a confirmed match: one or more requirements still need to be "
                        "verified for this facility. Ranked here using only the evidence already "
                        "available; confirming the missing evidence can only hold or improve this rank."
                    )
                ),
            }

    selected_ids = {str(row.get("canonical_facility_id")) for row in selected}
    complete_selected = [row for row in nice_complete_rows if str(row.get("canonical_facility_id")) in selected_ids]
    complete_beyond_display = [row for row in nice_complete_rows if str(row.get("canonical_facility_id")) not in selected_ids]
    pending_in_display_count = sum(1 for row in selected if row.get("must_eligibility") == "MUST_PENDING_VERIFICATION")

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
        "candidate_dispositions": [
            {
                "canonical_facility_id": row.get("canonical_facility_id"),
                "must_eligibility": row.get("must_eligibility"),
                "reason_code": row.get("must_disposition_reason"),
                "must_pass": list((row.get("client_intent_fit") or {}).get("must_pass") or []),
                "must_unknown": list((row.get("client_intent_fit") or {}).get("must_unknown") or []),
                "must_fail": list((row.get("client_intent_fit") or {}).get("must_fail") or []),
            }
            for row in rows
        ],
        "ai_ranking": ai_status,
        "ai_ranking_required": _env_true("OPTIME_AI_CANDIDATE_RANKING_REQUIRED"),
        "ai_ranking_fail_closed": ai_failure_block,
        "dynamic_preferences": dynamic_summary,
        "legacy_structured_nice_audit": structured_nice_summary,
        "legacy_structured_nice_authoritative": False,
        "top_nice_complete_count": len(complete_selected),
        "top_nice_complete_candidate_ids": [str(row.get("canonical_facility_id")) for row in complete_selected],
        "nice_complete_beyond_display_count": len(complete_beyond_display),
        "nice_complete_beyond_display_candidate_ids": [str(row.get("canonical_facility_id")) for row in complete_beyond_display],
        "client_statement": (
            (
                "We cannot present a recommendation yet because the required AI ranking did not complete successfully. The deterministic candidate order is retained only for diagnostics and is not exposed as a recommendation."
                if ai_failure_block
                else (
                    (
                        f"We currently have {len(complete_selected)} top-ranked facilities that pass every MUST requirement and have governed evidence matching every specific preference you expressed. This ranking can still change when we verify missing provider facts directly with the facilities."
                        + (
                            f" We also found {len(complete_beyond_display)} additional facility(ies) further down the ranked list that fully match every preference you expressed; ask to see them for a wider comparison."
                            if complete_beyond_display
                            else ""
                        )
                    )
                    if preference_count and complete_selected
                    else (
                        (
                            "The displayed facilities pass every verified MUST requirement. Some of your specific preferences are still unverified, so this ranking is provisional and direct provider verification can materially improve it."
                            + (
                                f" We did find {len(complete_beyond_display)} facility(ies) further down the ranked list that fully match every preference you expressed; ask to see them if a complete preference match matters more than AI rank order."
                                if complete_beyond_display
                                else ""
                            )
                        )
                        if preference_count
                        else "The displayed facilities pass every verified MUST requirement. No explicit NICE preference-completeness claim is being made; provider verification can still improve the ranking."
                    )
                )
            )
            + (
                f" {pending_in_display_count} of the facilities shown still have at least one MUST requirement pending verification rather than confirmed -- they are ranked on the evidence available today, unverified items are not counted against them, and confirming those items can only hold or improve their position, never worsen it."
                if pending_in_display_count and not ai_failure_block
                else ""
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
        decision["ai_ranking_failure"] = {
            "status": ai_status.get("status"),
            "candidate_count": len(rankable),
            "deterministic_order_exposed": False,
            "rule": "AI-owned ranking failure must fail closed rather than masquerade as an AI recommendation.",
        }
    result["decision_intelligence"] = decision
    return result


__all__ = ["apply_must_ai_nice_pipeline"]

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
7. An unavailable AI ranking never erases the deterministic MUST-qualified set. The
   verified eligible rows remain visible as a degraded, explicitly unranked result.
8. AI-blended judgment is skipped -- not attempted and not failed -- when a candidate
   pool has no real evidence for it to differentiate on: no NICE preferences to
   verify, and no candidate has any known rating, review count, regulatory grade, or
   disciplinary record. Forcing an AI score in that situation would produce a
   plausible-looking number with nothing real behind it. The client-specified order
   for this case -- MUST already applied, then NICE, then regulatory grade, then
   reviews -- is exactly what the deterministic governed key (intent_rank_key)
   computes, so it is used directly and shown as the actual recommendation, not
   quarantined as a failure-mode diagnostic.
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


def _rank_group_key(row: Dict[str, Any]) -> tuple[Any, ...]:
    """The value two rows must share to be a genuine tie in the *actual* order this
    pipeline produced.

    This stage re-sorts and re-assigns rank_position after _apply_combined_care_layer
    already ran (see app/services/__init__.py) -- its own rank_tie_status there does
    not survive here. When AI ranking succeeded, the real sort key was the AI's
    global_score (see ai_candidate_ranking_runtime._batch_ai_rank); when it did not,
    the real sort key was _fallback_key. Either way, the trailing facility-name
    tiebreaker isn't a real signal, so it's excluded from what counts as a tie.
    """
    ai_ranking = row.get("ai_ranking") if isinstance(row.get("ai_ranking"), dict) else {}
    global_score = ai_ranking.get("global_score")
    if isinstance(global_score, (int, float)):
        return ("AI_SCORE", round(float(global_score), 3))
    return ("DETERMINISTIC", *_fallback_key(row)[:-1])


def _has_differentiating_evidence(rows: List[Dict[str, Any]], dynamic_preferences: Dict[str, Any]) -> bool:
    """Whether this candidate pool has anything real for AI-blended judgment to
    differentiate on, beyond MUST (already the gate before this is ever called).

    If a client has NICE preferences, verifying them against governed evidence is
    real differentiating work an AI can meaningfully do. Otherwise, this checks the
    same raw signals intent_rank_key ranks on (rating, review count, regulatory
    grade, disciplinary record) -- if not one candidate in the pool has any of
    these on record, there is nothing for the AI to have a real opinion about, and
    asking it for one just produces noise dressed up as judgment.
    """
    if dynamic_preferences.get("preference_count"):
        return True
    for row in rows:
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        reputation = fit.get("public_reputation") if isinstance(fit.get("public_reputation"), dict) else {}
        history = row.get("regulatory_history") if isinstance(row.get("regulatory_history"), dict) else {}
        if isinstance(reputation.get("rating"), (int, float)):
            return True
        if isinstance(reputation.get("review_count"), int):
            return True
        grade = str(history.get("latest_known_grade") or "").upper()
        if grade and grade != "UNKNOWN":
            return True
        if str(history.get("disciplinary_action") or "").upper() == "Y":
            return True
    return False


def _deterministic_waterfall_rank(rows: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Rank by the governed deterministic key directly -- see module docstring
    point 8. Same ai_ranking row shape as the AI paths (minus global_score, which
    _rank_group_key correctly reads as "no AI score, use the deterministic key" for
    tie detection -- exactly the right behavior here too)."""
    ranked = sorted(rows, key=_fallback_key)
    for position, row in enumerate(ranked, start=1):
        row["ai_ranking"] = {
            "status": "DETERMINISTIC_THIN_EVIDENCE_WATERFALL",
            "rank": position,
            "reason": "No NICE preferences and no candidate in this set has any known rating, review count, regulatory grade, or disciplinary record. Ranked by the governed deterministic order (MUST, then NICE, then regulatory grade, then reviews) instead of AI-blended judgment, which would have nothing real to differentiate on.",
            "information_deficits": [],
            "rank_drivers": [],
            "rank_risks": [],
        }
    ai_status = {
        "status": "DETERMINISTIC_THIN_EVIDENCE_WATERFALL",
        "candidate_count": len(ranked),
        "closed_world_validated": True,
        "reason": "No differentiating evidence available for AI judgment in this candidate pool.",
    }
    return ranked, ai_status


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


def _resolve_interactive_shortlist_limit(requested_limit: int) -> int:
    """Keep live AI work to the shortlist a family can use now."""
    configured = int(os.getenv("OPTIME_INTERACTIVE_SHORTLIST_LIMIT", "10"))
    return max(5, min(20, configured, max(5, int(requested_limit or 0))))


def _defer_dynamic_preference_verification(
    rows: List[Dict[str, Any]], dynamic_preferences: Dict[str, Any]
) -> Dict[str, Any]:
    """Preserve unknown preference evidence without blocking a live search."""
    preferences = list(dynamic_preferences.get("preferences") or [])
    for row in rows:
        assessments = [
            {
                "preference_id": str(pref.get("preference_id")),
                "status": "UNKNOWN",
                "supporting_claim_ids": [],
                "reason": "Facility-specific preference evidence is still being researched.",
                "provider_question_if_unknown": f"Please verify whether this community satisfies: {pref.get('semantic_meaning')}",
            }
            for pref in preferences
        ]
        row["dynamic_preference_fit"] = {
            "status": "PENDING_EVIDENCE_RESEARCH",
            "assessments": assessments,
            "required_preference_ids": [str(pref.get("preference_id")) for pref in preferences],
        }
        row["nice_to_have_coverage"] = {
            "status": "NICE_UNVERIFIED",
            "required": [str(pref.get("preference_id")) for pref in preferences],
            "verified_match": [],
            "unresolved": [str(pref.get("preference_id")) for pref in preferences],
            "verified_match_count": 0,
            "required_count": len(preferences),
            "source": "PENDING_GOVERNED_EVIDENCE_RESEARCH",
        }
    return {
        "status": "DEFERRED_TO_EVIDENCE_RESEARCH",
        "preference_count": len(preferences),
        "nice_complete_candidate_count": 0,
        "verification_required_count": len(rows) if preferences else 0,
        "verification_execution": "NOT_RUN_IN_LIVE_SEARCH",
        "rule": "Unknown preference evidence is shown as research-needed; it is never treated as a mismatch.",
    }


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
    # The full universe remains gated and enters evidence research. Live candidate AI
    # works only on the small shortlist that can be shown usefully right now.
    rankable = eligible + pending
    rankable.sort(key=_fallback_key)
    interactive_shortlist_limit = _resolve_interactive_shortlist_limit(limit)
    live_shortlist = rankable[:interactive_shortlist_limit]

    audit_intent = deepcopy(client_intent)
    _remove_legacy_nice_from_authoritative_path(live_shortlist)
    ranking_intent = deepcopy(client_intent)
    ranking_intent["nice_to_haves"] = []

    thin_evidence_bypass = bool(live_shortlist) and not _has_differentiating_evidence(live_shortlist, dynamic_preferences)
    if thin_evidence_bypass:
        ranked, ai_status = _deterministic_waterfall_rank(live_shortlist)
    else:
        ranked, ai_status = rank_must_eligible_candidates(
            live_shortlist,
            client_intent=ranking_intent,
            human_context=human_context,
            strategy=strategy,
            deterministic_fallback_key=_fallback_key,
        )

    ai_ranking_degraded = (
        not thin_evidence_bypass
        and bool(live_shortlist)
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

    selected = ranked[: max(0, int(limit or 0))]
    if _env_true("OPTIME_LIVE_PREFERENCE_VERIFICATION"):
        dynamic_summary, nice_complete_rows = _verify_dynamic_preferences_in_waves(
            ranked, dynamic_preferences, len(ranked)
        )
    else:
        dynamic_summary = _defer_dynamic_preference_verification(
            ranked, dynamic_preferences
        )
        nice_complete_rows = []

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

    group_keys = [_rank_group_key(row) for row in ranked]
    for position, row in enumerate(ranked, start=1):
        row["rank_position"] = position
        row["rank_display"] = f"#{position}"
        tied_indexes = [
            other for other, key in enumerate(group_keys)
            if other != position - 1 and key == group_keys[position - 1]
        ]
        row["rank_tie_status"] = "JOINT_RANK" if tied_indexes else "UNIQUE_RANK"
        row["tied_with"] = [ranked[i].get("facility_name") for i in tied_indexes]
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
            "SEMANTIC_AI_RANK_INTERACTIVE_SHORTLIST",
            "EVIDENCE_RESEARCH_CONTINUES_AFTER_LIVE_RESPONSE",
            "PROVIDER_FACT_VERIFICATION",
            "AI_RERANK_AFTER_NEW_EVIDENCE",
        ],
        "must_eligible_count": len(eligible),
        "must_pending_verification_count": len(pending),
        "must_rejected_count": len(rejected),
        "interactive_shortlist_limit": interactive_shortlist_limit,
        "full_rankable_candidate_count": len(rankable),
        "ranking_scope": "LIVE_SHORTLIST_ONLY_FULL_UNIVERSE_RESEARCH_CONTINUES",
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
        "ai_ranking_fail_closed": False,
        "ai_ranking_degraded": ai_ranking_degraded,
        "dynamic_preferences": dynamic_summary,
        "legacy_structured_nice_audit": structured_nice_summary,
        "legacy_structured_nice_authoritative": False,
        "top_nice_complete_count": len(complete_selected),
        "top_nice_complete_candidate_ids": [str(row.get("canonical_facility_id")) for row in complete_selected],
        "nice_complete_beyond_display_count": len(complete_beyond_display),
        "nice_complete_beyond_display_candidate_ids": [str(row.get("canonical_facility_id")) for row in complete_beyond_display],
        "client_statement": (
            (
                "The ranking enhancement was unavailable. We are showing facilities that meet the verified hard requirements as an explicitly degraded, unranked set; provider details still require confirmation."
                if ai_ranking_degraded
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
                            "The displayed facilities pass every verified MUST requirement. Some of your specific preferences are still being researched, so this ranking is provisional and direct provider verification can materially improve it."
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
                if pending_in_display_count and not ai_ranking_degraded
                else ""
            )
        ),
        "rule": "AI never decides MUST eligibility or whether verified candidates disappear. If AI ranking is unavailable, the deterministic MUST-qualified set remains visible as degraded and unranked. MATCH/MISMATCH requires governed facility claims; otherwise the preference remains UNKNOWN.",
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

    if ai_ranking_degraded:
        decision["ai_ranking_failure"] = {
            "status": ai_status.get("status"),
            "candidate_count": len(live_shortlist),
            "deterministic_order_exposed": True,
            "presentation": "DEGRADED_UNRANKED_ELIGIBLE_SET",
            "rule": "AI ranking failure may remove AI ordering, but it may not erase the deterministic MUST-qualified candidate set.",
        }
    result["decision_intelligence"] = decision
    return result


__all__ = ["apply_must_ai_nice_pipeline"]

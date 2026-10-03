from __future__ import annotations

"""Final facility selection pipeline.

1. Deterministic MUST gate, no AI discretion.
2. Deterministic governed evidence ranks MUST_ELIGIBLE rows; AI has no ranking authority.
3. Dynamic preference verification is evidence-closed-world: MATCH/MISMATCH requires
   governed claims; missing evidence stays UNKNOWN.
4. Structured preference evidence participates in governed deterministic ranking;
   unresolved structured or dynamic preferences keep the result provisional.
5. Pending MUST candidates remain in a research queue; only verified eligible
   candidates enter the recommendation pool. UNKNOWN is never a mismatch.
6. Compare the complete eligible universe before bounded verification and display.
   Provider evidence can update a future deterministic comparison; AI cannot rank.
"""

from copy import deepcopy
import os
from typing import Any, Dict, List

from app.services.ai_candidate_ranking_runtime import attach_nice_coverage, rank_must_eligible_candidates  # compatibility symbol; never called by production pipeline
from app.services.client_intent_runtime import intent_rank_key
from app.services.human_intelligence_runtime_verified import person_fit_sort_key
from app.services.semantic_preference_runtime import build_dynamic_preference_model, verify_dynamic_preferences, preference_verification_question


def _fallback_key(row: Dict[str, Any]) -> tuple[Any, ...]:
    return (*person_fit_sort_key(row), *intent_rank_key(row))


# intent_rank_key = (gate, care setting, NICE match, NICE mismatch, community fit known,
# community fit, <regulatory...>, <reputation...>, <evidence counts>). The family's own
# criteria are the first six; everything after is government/quality/reputation evidence,
# which belongs to the Regulatory/Quality Evidence Layer and is applied there instead.
_FAMILY_CRITERIA_LENGTH = 6

# Names describe the exact component order supplied to _layered_rank. They do
# not add criteria or weights. Snapshot shape validation fails honestly if that
# comparator later changes without updating its explanation contract.
_FINAL_BASE_DIMENSIONS = (
    ("strict_budget_before_expansion", "This option fits the stated monthly budget; the next option uses the permitted budget expansion."),
    ("community_preference_evidence", "Verified evidence for your community preference distinguishes these options."),
    ("community_preference_fit", "This option better matches your stated community preference."),
    ("must_gate", "The recorded requirements gate distinguishes these options."),
    ("care_setting_fit", "The recorded care setting fit places this option higher."),
    ("verified_preference_matches", "This option has more verified matches to your stated preferences."),
    ("verified_preference_mismatches", "This option has fewer verified mismatches to your stated preferences."),
    ("community_environment_evidence", "Verified evidence for your requested community environment distinguishes these options."),
    ("community_environment_fit", "This option better matches your requested community environment."),
    ("nearby_comparison_scope", "The recorded nearby comparison scope distinguishes these options."),
    ("requested_nearby_fit", "This option has a better recorded fit for the nearby places you requested."),
    ("requested_nearby_distance", "This option is closer to the nearby places you requested, after the earlier criteria were equal."),
)


def _family_criteria_key(row: Dict[str, Any]) -> tuple[Any, ...]:
    from app.services.nearby_place_service import nearby_rank_key
    nearby = row.get("nearby_place_fit") or {}
    return (*person_fit_sort_key(row), *intent_rank_key(row)[:_FAMILY_CRITERIA_LENGTH],
            *nearby_rank_key(row, str(nearby.get("importance") or "No preference")))


def _layered_rank(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from app.services.regulatory_quality_layer import rank_with_evidence_layer
    return rank_with_evidence_layer(rows, lambda row: (1 if row.get("budget_exception") else 0, *_family_criteria_key(row)))


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
        return (bool(row.get("budget_exception")), "AI_SCORE", round(float(global_score), 3))
    if row.get("rank_group_signature") is not None:
        return (bool(row.get("budget_exception")), "LAYERED", row["rank_group_signature"])
    return (bool(row.get("budget_exception")), "DETERMINISTIC", *_fallback_key(row)[:-1])


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
    # A client-stated MUST (dialysis, wound care, clinical acuity, memory care, kosher,
    # language, budget, Medicaid -- see semantic_facility_requirements.py) that some
    # candidates in this pool already have confirmed and others don't is real,
    # client-relevant differentiation for the AI to reason about, even when none of
    # them has a star rating or regulatory grade yet. Likewise a care-setting-fit tier
    # split (e.g. some PRIMARY_FIT, some POSSIBLE_FIT) is a real distinction the
    # alphabetical fallback order does not otherwise surface.
    must_pass_signatures = {
        tuple(sorted((row.get("client_intent_fit") or {}).get("must_pass") or []))
        for row in rows
    }
    if len(must_pass_signatures) > 1:
        return True
    care_setting_statuses = {(row.get("care_setting_fit") or {}).get("status") for row in rows}
    if len(care_setting_statuses) > 1:
        return True
    return False


def _deterministic_waterfall_rank(rows: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Rank by the governed deterministic key directly -- see module docstring
    point 8. Same ai_ranking row shape as the AI paths (minus global_score, which
    _rank_group_key correctly reads as "no AI score, use the deterministic key" for
    tie detection -- exactly the right behavior here too)."""
    ranked = _layered_rank(list(rows))
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
    return str(ai_status.get("status") or "").upper() in {"AI_RANKED", "AI_BATCH_RANKED", "AI_BATCH_RANKED_RECOVERY"}


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
                "provider_question_if_unknown": preference_verification_question(pref, dynamic_preferences),
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
            # The governed MUST decision is the final recommendation authority.
            # Keep legacy evidence fields for audit, but do not expose a contradictory
            # POTENTIALLY_ELIGIBLE/INSUFFICIENT_EVIDENCE status on an approved card.
            row["legacy_eligibility_status"] = row.get("eligibility_status")
            row["eligibility_status"] = "ELIGIBLE"
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

    # Pending MUST evidence is a research queue, never a recommendation pool.
    rankable = list(eligible)
    budget = questionnaire_state.get("budget")
    if isinstance(budget, (int, float)) and not isinstance(budget, bool) and budget > 0:
        from app.services.affordability_floor import relevant_monthly_cost
        for row in rankable:
            # Compared with the cost under the family's funding pathway (private pay, or
            # household out-of-pocket under Medicaid) -- affordability_floor.py.
            price = relevant_monthly_cost(row)
            if isinstance(price, (int, float)) and not isinstance(price, bool):
                variance = (float(price) - float(budget)) / float(budget)
                row["budget_variance_pct"] = round(variance * 100, 1)
                row["budget_band"] = "OVER_BUDGET_WITHIN_10_PERCENT" if variance > 0 else ("AT_OR_WITHIN_10_PERCENT_BELOW" if variance >= -0.10 else "MORE_THAN_10_PERCENT_BELOW")
                row["budget_exception"] = variance > 0
        # In-budget candidates always rank ahead of the permitted +10% expansion.
        # The normal ranking still decides quality within each band.
    # The shortlist cut uses the same layered order as the final ranking.
    rankable = _layered_rank(rankable)
    decision["ranking_universe_audit"] = {
        "eligible_candidate_count": len(rankable),
        "eligible_candidate_order": [row.get("canonical_facility_id") for row in rankable],
        "order": "BUDGET_BAND_THEN_EXPLICIT_PERSON_FIT_THEN_VERIFIED_NICE_THEN_REGULATORY_QUALITY",
        "shortlist_applied_after_full_universe_ranking": True,
    }
    interactive_shortlist_limit = _resolve_interactive_shortlist_limit(limit)
    live_shortlist = rankable[:interactive_shortlist_limit]

    audit_intent = deepcopy(client_intent)
    # Structured NICE evidence remains part of the deterministic ranking key. It is
    # evidence, not a second decision engine. Dynamic/open-ended preferences remain
    # UNKNOWN until verified and therefore cannot invent a ranking advantage.
    ranking_intent = deepcopy(client_intent)

    # Single ranking authority: governed deterministic evidence. Candidate-ranking
    # AI is intentionally outside the production decision path; it may not break ties
    # or reorder facilities. Budget band remains the first ordering partition.
    ranked, deterministic_status = _deterministic_waterfall_rank(live_shortlist)
    ranked.sort(key=lambda row: bool(row.get("budget_exception")))
    ai_status = {
        "status": "DETERMINISTIC_THIN_EVIDENCE_WATERFALL",
        "authority": "DETERMINISTIC_DECISION_ENGINE",
        "candidate_count": len(ranked),
        "deterministic_status": deterministic_status,
    }
    ai_ranking_degraded = False
    thin_evidence_bypass = True

    audit_rows = deepcopy(ranked)
    for audit_row in audit_rows:
        legacy = audit_row.get("legacy_structured_nice_fit") if isinstance(audit_row.get("legacy_structured_nice_fit"), dict) else {}
        fit = audit_row.get("client_intent_fit") if isinstance(audit_row.get("client_intent_fit"), dict) else {}
        fit["nice_match"] = list(legacy.get("nice_match", fit.get("nice_match")) or [])
        fit["nice_unknown"] = list(legacy.get("nice_unknown", fit.get("nice_unknown")) or [])
        fit["nice_fit_scores"] = dict(legacy.get("nice_fit_scores", fit.get("nice_fit_scores")) or {})
        # The final budget gate can learn a price after the earlier fit snapshot.
        # Reuse that exact governed proof; a boolean published-rate claim is insufficient.
        from app.services.affordability_floor import relevant_monthly_cost
        cost = relevant_monthly_cost(audit_row)
        if ("SEMANTIC_BUDGET_VERIFICATION" in (fit.get("must_pass") or [])
                and isinstance(budget, (int, float)) and not isinstance(budget, bool)
                and budget > 0 and cost is not None and cost <= budget):
            if "BUDGET_FIT" not in fit["nice_match"]:
                fit["nice_match"].append("BUDGET_FIT")
            fit["nice_unknown"] = [key for key in fit["nice_unknown"] if key != "BUDGET_FIT"]
    structured_nice_summary = attach_nice_coverage(audit_rows, audit_intent)
    for row, audit_row in zip(ranked, audit_rows):
        # Keep evidence already used by deterministic ranking visible without
        # claiming it proves an arbitrary, narrower semantic preference.
        row["structured_nice_to_have_coverage"] = audit_row.get("nice_to_have_coverage")

    selected = ranked[: max(0, int(limit or 0))]
    capital_review = []
    for row in selected:
        fee = row.get("entrance_fee")
        if isinstance(fee, (int, float)) and not isinstance(fee, bool) and fee > 0:
            row["one_time_cost_review"] = {
                "status": "FAMILY_AND_PROVIDER_CONFIRMATION_REQUIRED",
                "amount": fee,
                "provider_question": "Does this entrance fee apply to the specific care program and admission contract offered?",
                "family_question": "Can the household fund this one-time fee separately from the monthly budget?",
                "rule": "A monthly budget match is not proof of one-time capital affordability.",
            }
            capital_review.append(row.get("canonical_facility_id"))
    decision["financial_review"] = {"status": "PENDING_ONE_TIME_COST_CONFIRMATION" if capital_review else "NO_KNOWN_ONE_TIME_COST_REVIEW",
                                    "candidate_ids": capital_review}
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
    first_position_by_group: Dict[tuple[Any, ...], int] = {}
    for position, key in enumerate(group_keys, start=1):
        first_position_by_group.setdefault(key, position)

    # Earlier pair explanations can describe a different comparator. Only a
    # snapshot from the final full-universe comparison can explain this stage.
    from app.services.regulatory_quality_layer import explain_ranked_pair
    existing_tie_breaks = {
        (
            str(item.get("higher_canonical_facility_id") or ""),
            str(item.get("lower_canonical_facility_id") or ""),
        ): item
        for item in result.get("tie_break_decisions") or []
        if isinstance(item, dict)
    }
    final_tie_breaks: List[Dict[str, Any]] = []
    for position, row in enumerate(ranked, start=1):
        group_key = group_keys[position - 1]
        rank_position = first_position_by_group[group_key]
        tied_indexes = [
            other for other, key in enumerate(group_keys)
            if other != position - 1 and key == group_key
        ]
        is_joint_rank = bool(tied_indexes)
        row["rank_position"] = rank_position
        row["rank_display"] = f"Joint #{rank_position}" if is_joint_rank else f"#{rank_position}"
        row["rank_tie_status"] = "JOINT_RANK" if is_joint_rank else "UNIQUE_RANK"
        row["tied_with"] = [ranked[i].get("facility_name") for i in tied_indexes]
        if is_joint_rank:
            row["tie_break_explanation_vs_next"] = {
                "why_ranked_above": "No governed ranking difference was verified within this tied group.",
                "deciding_dimension": "true_tie",
                "remained_equal": ["final_authoritative_ranking_key"],
                "remaining_unknown": [],
            }
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

        if position < len(ranked):
            following = ranked[position]
            pair = (
                str(row.get("canonical_facility_id") or ""),
                str(following.get("canonical_facility_id") or ""),
            )
            if group_key == group_keys[position]:
                final_tie_breaks.append({
                    "higher_canonical_facility_id": pair[0],
                    "lower_canonical_facility_id": pair[1],
                    "decision_dimension": "true_tie",
                    "reason": "No governed ranking difference was verified at this comparison step.",
                    "equal_dimensions": ["final_authoritative_ranking_key"],
                    "unknown_dimensions": [],
                    "deterministic_display_order": True,
                })
            elif not row.get("budget_exception") and following.get("budget_exception"):
                reason = "This option fits the stated monthly budget; the next option uses the permitted budget expansion."
                row["tie_break_explanation_vs_next"] = {"why_ranked_above": reason, "deciding_dimension": "strict_budget_before_expansion", "remained_equal": [], "remaining_unknown": []}
                final_tie_breaks.append({"higher_canonical_facility_id": pair[0], "lower_canonical_facility_id": pair[1], "decision_dimension": "strict_budget_before_expansion", "reason": reason, "equal_dimensions": [], "unknown_dimensions": []})
            elif _ai_ranking_succeeded(ai_status):
                # The previous deterministic comparison does not explain an AI
                # rerank. Record every unequal final pair, so the UI cannot turn
                # a missing old pair into a false "True tie" or stale staffing claim.
                ranking = row.get("ai_ranking") or {}
                reason = str(ranking.get("reason") or "AI assessment of this resident's needs and the supplied evidence places this option higher.")
                if ranking.get("citation_validation") == "PARTIAL":
                    reason += " Some supporting comparison references remain unverified."
                row["tie_break_explanation_vs_next"] = {
                    "why_ranked_above": reason,
                    "deciding_dimension": "resident_specific_ai_assessment",
                    "remained_equal": [],
                    "remaining_unknown": list(ranking.get("information_deficits") or []),
                }
                final_tie_breaks.append({
                    "higher_canonical_facility_id": pair[0],
                    "lower_canonical_facility_id": pair[1],
                    "decision_dimension": "resident_specific_ai_assessment",
                    "reason": reason,
                    "equal_dimensions": [],
                    "unknown_dimensions": list(ranking.get("information_deficits") or []),
                })
            elif (comparison := explain_ranked_pair(row, following, _FINAL_BASE_DIMENSIONS)) is not None:
                row["tie_break_explanation_vs_next"] = {
                    "why_ranked_above": comparison["reason"],
                    "deciding_dimension": comparison["decision_dimension"],
                    "remained_equal": comparison["equal_dimensions"],
                    "remaining_unknown": comparison["unknown_dimensions"],
                    "comparison_evidence": comparison.get("comparison_evidence"),
                }
                final_tie_breaks.append({"higher_canonical_facility_id": pair[0], "lower_canonical_facility_id": pair[1], **comparison})
            elif pair in existing_tie_breaks and not row.get("__rank_comparison_trace"):
                row["tie_break_explanation_vs_next"] = {
                    "why_ranked_above": existing_tie_breaks[pair].get("reason") or "Ranked by the governed deterministic comparison.",
                    "deciding_dimension": existing_tie_breaks[pair].get("decision_dimension"),
                    "remained_equal": existing_tie_breaks[pair].get("equal_dimensions") or [],
                    "remaining_unknown": existing_tie_breaks[pair].get("unknown_dimensions") or [],
                }
                final_tie_breaks.append(existing_tie_breaks[pair])
            else:
                reason = "The governed comparison orders these options differently; a specific comparison explanation is not yet available."
                row["tie_break_explanation_vs_next"] = {"why_ranked_above": reason, "deciding_dimension": "final_authoritative_ranking_key", "remained_equal": [], "remaining_unknown": ["comparison explanation"]}
                final_tie_breaks.append({"higher_canonical_facility_id": pair[0], "lower_canonical_facility_id": pair[1], "decision_dimension": "final_authoritative_ranking_key", "reason": reason, "equal_dimensions": [], "unknown_dimensions": ["comparison explanation"]})
        elif not is_joint_rank:
            row.pop("tie_break_explanation_vs_next", None)

    selected_ids = {str(row.get("canonical_facility_id")) for row in selected}
    complete_selected = [row for row in nice_complete_rows if str(row.get("canonical_facility_id")) in selected_ids]
    complete_beyond_display = [row for row in nice_complete_rows if str(row.get("canonical_facility_id")) not in selected_ids]
    pending_in_display_count = sum(1 for row in selected if row.get("must_eligibility") == "MUST_PENDING_VERIFICATION")

    result["results"] = selected
    result["tie_break_decisions"] = final_tie_breaks
    result["result_count"] = len(selected)
    result["must_eligible_count"] = len(eligible)
    result["must_pending_verification_count"] = len(pending)
    result["must_rejected_count"] = len(rejected)
    result["must_pending_verification_candidates"] = [
        {
            "canonical_facility_id": row.get("canonical_facility_id"),
            "facility_name": row.get("facility_name"),
            "must_unknown": (row.get("client_intent_fit") or {}).get("must_unknown") or [],
            "must_pass": (row.get("client_intent_fit") or {}).get("must_pass") or [],
            "must_fail": (row.get("client_intent_fit") or {}).get("must_fail") or [],
            "starting_monthly_price": row.get("starting_monthly_price"),
            "eligibility_status": row.get("eligibility_status"),
            "synthetic_pilot": row.get("synthetic_pilot") is True,
        }
        for row in pending
    ]

    preference_count = int(dynamic_preferences.get("preference_count") or 0)
    decision["facility_selection_pipeline"] = {
        "version": "must-ai-dynamic-preferences-v4",
        "order": [
            "DETERMINISTIC_MUST_GATE",
            "SEMANTIC_AI_DYNAMIC_PREFERENCE_MODEL",
            "DETERMINISTIC_FULL_UNIVERSE_COMPARISON",
            "EVIDENCE_RESEARCH_CONTINUES_AFTER_LIVE_RESPONSE",
            "PROVIDER_FACT_VERIFICATION",
            "AI_RERANK_AFTER_NEW_EVIDENCE",
        ],
        "must_eligible_count": len(eligible),
        "must_pending_verification_count": len(pending),
        "must_rejected_count": len(rejected),
        "interactive_shortlist_limit": interactive_shortlist_limit,
        "full_rankable_candidate_count": len(rankable),
        "ranking_scope": "FULL_ELIGIBLE_UNIVERSE_DETERMINISTIC_ORDER",
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
        "ai_ranking_required": False,
        "ai_ranking_fail_closed": False,
        "ai_ranking_degraded": ai_ranking_degraded,
        "dynamic_preferences": dynamic_summary,
        "legacy_structured_nice_audit": structured_nice_summary,
        "selected_structured_preferences": {
            "candidate_count": len(selected),
            "unresolved_candidate_count": sum(bool((row.get("structured_nice_to_have_coverage") or {}).get("unresolved")) for row in selected),
            "unresolved_candidate_ids": [row.get("canonical_facility_id") for row in selected if (row.get("structured_nice_to_have_coverage") or {}).get("unresolved")],
        },
        "legacy_structured_nice_authoritative": False,
        "governed_structured_nice_authoritative": True,
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
        "DETERMINISTIC_GOVERNED_NICE_EVIDENCE",
        "GOVERNMENT_REGULATORY_DATA",
        "PUBLIC_REPUTATION",
        "RELEVANT_EVIDENCE_COMPLETENESS",
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

"""Preference sensitivity over the complete eligible pool; never a ranking authority."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable
from app.services.oomniker_nth_contract import LABELS, NEARBY, acceptance_for, remove_nice, safe_nth_keys, waive_nth

DISPLAY_LIMIT = 5
_IMPLICIT = {"BUDGET_FIT", "AVAILABILITY_FIT"}
_LEVER_PATHS = {
    "COMMUNITY_ENVIRONMENT_MATCH": "humanIntelligenceV2.personalityProfile.communitySizePreference",
    "PREFERRED_LANGUAGE_SUPPORT": "humanIntelligenceV2.languageProfile.languageNeedScope",
    "CONTINUUM_OF_CARE": "humanIntelligenceV2.futureCareProfile.continuumOfCarePreference",
}
_PROTECTED = {"PREFERRED_LANGUAGE_SUPPORT": {"REQUIRED_LANGUAGE_SUPPORT", "SEMANTIC_LANGUAGE_SUPPORT"},
              "CONTINUUM_OF_CARE": {"CONTINUUM_OF_CARE_REQUIRED", "SEMANTIC_FUTURE_CARE_PATH"}}


def _get(profile: dict, path: str) -> Any:
    value = profile
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _identity(row: dict) -> str:
    return str(row.get("canonical_facility_id") or "")


def _fit(row: dict) -> dict:
    return row.get("client_intent_fit") or {}


def _remove_nice(row: dict, key: str) -> None:
    remove_nice(row, key)


def _matches(row: dict, key: str) -> bool:
    if key == NEARBY:
        nearby = row.get("nearby_place_fit") or {}
        return (nearby.get("status") == "KNOWN" and bool(nearby.get("requested_categories"))
                and nearby.get("matched_categories") == nearby.get("requested_categories"))
    return key in (_fit(row).get("nice_match") or [])


def _mismatches(row: dict, key: str) -> bool:
    if key == NEARBY:
        nearby = row.get("nearby_place_fit") or {}
        return nearby.get("status") == "KNOWN" and not _matches(row, key)
    return key in (_fit(row).get("nice_mismatch") or [])


def _quality_advantage(candidate: dict, displaced: list[dict]) -> dict | None:
    from app.services.regulatory_quality_layer import MEASURES, measure_values
    values = measure_values(candidate)
    # Evidence completeness is not a facility quality rating.
    for other in displaced:
        comparison = measure_values(other)
        for key, layer, direction in MEASURES:
            if layer == "RELEVANT_EVIDENCE" or key not in values or key not in comparison:
                continue
            source, value = values[key]
            other_source, baseline = comparison[key]
            if source != other_source or source == "UNKNOWN_SOURCE":
                continue
            if value == baseline:
                continue
            better = value > baseline if direction == "higher" else value < baseline
            if better:
                return {"parameter": key, "source_family": source, "value": value,
                        "compared_value": baseline, "compared_facility_id": _identity(other),
                        "direction": direction}
            break  # Do not cherry-pick a later measure after a worse priority measure.
    return None


def analyze_preferences(rows: list[dict], intent: dict, profile: dict,
                        rank: Callable[[list[dict]], list[dict]], *, display_limit: int = DISPLAY_LIMIT,
                        dynamic_preference_count: int = 0, dynamic_preferences: dict | None = None,
                        waived_keys: list[str] | None = None) -> dict:
    """Rerank isolated copies. Original MUST decisions and recommendation order survive.

    Supported canonical levers are explicit, extensible contracts. Unsupported NICEs
    still receive evidence diagnostics; they cannot produce an unverified promise.
    """
    ids = [_identity(row) for row in rows]
    if not all(ids) or len(set(ids)) != len(ids):
        return {"status": "INVALID_IDENTITIES", "suggestions": [], "parameters": []}
    eligible = [deepcopy(row) for row in rows if _fit(row).get("hard_gate") == "PASS"
                and not _fit(row).get("must_fail") and not _fit(row).get("must_unknown")]
    original = rank(deepcopy(eligible))
    window = min(DISPLAY_LIMIT, max(0, display_limit))
    baseline = original[:window]
    baseline_ids = {_identity(row) for row in baseline}
    musts = {str(item.get("key") or "") for item in intent.get("must_haves") or []}
    nice_keys = {str(item.get("key") or "") for item in intent.get("nice_to_haves") or []}
    safe_keys = safe_nth_keys(intent, profile)
    if NEARBY in safe_keys:
        nice_keys.add(NEARBY)
    nice_keys -= set(waived_keys or [])
    safe_keys -= set(waived_keys or [])
    ignored_neutral = []
    future_paths = ["humanIntelligenceV2.futureCareProfile.continuumOfCarePreference",
                    "humanIntelligenceV2.futureCareProfile.avoidFutureMovesPreference", "futureCarePreference"]
    if "CONTINUUM_OF_CARE" in nice_keys and not any(
            str(_get(profile, path) or "").strip().lower() in {"preferred", "important", "yes"} for path in future_paths):
        # Legacy intent may contain "important" inside "not important". The advisor
        # cannot offer a preference change the family has already declined.
        nice_keys.remove("CONTINUUM_OF_CARE")
        ignored_neutral.append("CONTINUUM_OF_CARE")
    parameters, suggestions = [], []
    for key in sorted(nice_keys - _IMPLICIT - {""}):
        diagnostic = {"parameter": key, "label": LABELS.get(key, key.replace("_", " ").title()), "excluded_by_preference_count": 0,
                      "verified_mismatch_count": sum(_mismatches(row, key) for row in eligible),
                      "unknown_count": sum(not _matches(row, key) and not _mismatches(row, key) for row in eligible),
                      "eligible_below_display_count": sum(_mismatches(row, key) and _identity(row) not in baseline_ids for row in eligible),
                      "new_recommendation_count": 0}
        parameters.append(diagnostic)
        if key not in safe_keys:
            diagnostic["status"] = "NO_SAFE_CANONICAL_LEVER"
            continue
        path = _LEVER_PATHS.get(key, "")
        value = _get(profile, path)
        choices: list[tuple[str, str, dict[str, str]]] = []
        if key == "COMMUNITY_ENVIRONMENT_MATCH":
            if value == "Small and familiar":
                choices = [("Medium", "MEDIUM", {path: "Medium"}), ("Large and active", "LARGE", {path: "Large and active"})]
            elif value == "Medium":
                choices = [("Large and active", "LARGE", {path: "Large and active"})]
        elif key == "PREFERRED_LANGUAGE_SUPPORT" and str(value or "").lower() in {"preference", "preferred"}:
            root = "humanIntelligenceV2.languageProfile."
            choices = [("No language preference", "", {root + "preferredSpokenLanguage": "No preference", root + "medicalDiscussionLanguage": "No preference"})]
        elif key == "CONTINUUM_OF_CARE":
            paths = [path, "humanIntelligenceV2.futureCareProfile.avoidFutureMovesPreference", "futureCarePreference"]
            if any(str(_get(profile, p) or "").lower() == "required" for p in paths):
                continue
            choices = [("No continuity preference", "", {p: "No preference" for p in paths})]
        # Every explicit NTH has the same executable neutral change. Both this
        # simulation and the consented production rerun use waive_nth, so no
        # speculative profile patch or invented capability is needed.
        choices.append((f"No priority for {diagnostic['label'].lower()}", "WAIVE", {}))
        for label, size_preference, patch in choices:
            remaining_dynamic = []
            for preference in (dynamic_preferences or {}).get("preferences") or []:
                paths = set(preference.get("mapped_parameters") or [])
                quote = str(preference.get("client_expression") or "").strip()
                # This exact, single-field quoted size answer has already been
                # recomputed from the governed size evidence. It is not a second
                # unresolved preference. Arbitrary/mixed narrative stays open-world.
                replaced_size_trace = (key == "COMMUNITY_ENVIRONMENT_MATCH" and paths == {path}
                                       and quote == str(value) and bool(size_preference))
                if not replaced_size_trace:
                    remaining_dynamic.append(str(preference.get("preference_id") or ""))
            simulated = deepcopy(eligible)
            for row in simulated:
                if size_preference == "WAIVE" or not size_preference:
                    waive_nth(row, key)
                else:
                    _remove_nice(row, key)
                if size_preference and size_preference != "WAIVE":
                    from app.services.human_intelligence_runtime import _size_fit
                    size = (row.get("human_person_fit") or {}).get("community_size") or {}
                    size["preference"] = size_preference
                    score = _size_fit(size_preference, str(size.get("community_size_band") or "UNKNOWN"))
                    size["fit_score"] = score if score is not None else "UNKNOWN"
                    fit = _fit(row)
                    if score is None:
                        fit.setdefault("nice_unknown", []).append(key)
                        if isinstance(fit.get("relevant_evidence_unknown_count"), int):
                            fit["relevant_evidence_unknown_count"] += 1
                    else:
                        fit.setdefault("nice_fit_scores", {})[key] = score
                        fit.setdefault("nice_match" if score >= 70 else "nice_mismatch", []).append(key)
                        if isinstance(fit.get("relevant_evidence_known_count"), int):
                            fit["relevant_evidence_known_count"] += 1
            full_after = rank(simulated)
            reranked = full_after[:window]
            promoted = [row for row in reranked if _identity(row) not in baseline_ids]
            diagnostic["new_recommendation_count"] = max(diagnostic["new_recommendation_count"], len(promoted))
            displaced = [row for row in baseline if _identity(row) not in {_identity(r) for r in reranked}]
            proven = []
            for row in promoted:
                fit = _fit(row)
                signature = row.get("rank_group_signature")
                if signature is not None and any(other.get("rank_group_signature") == signature for other in full_after[window:]):
                    continue  # A display-order change inside a true tie is not a rank gain.
                assessments = {str(a.get("preference_id")): a.get("status") for a in (row.get("dynamic_preference_fit") or {}).get("assessments") or []}
                if any(assessments.get(pref_id) not in {"MATCH", "NOT_APPLICABLE"} for pref_id in remaining_dynamic):
                    continue
                if dynamic_preference_count and dynamic_preferences is None and (row.get("dynamic_preference_fit") or {}).get("status") != "NICE_COMPLETE":
                    continue
                remaining = nice_keys - _IMPLICIT - {key}
                if not all(_matches(row, other) for other in remaining):
                    continue  # Cannot say all other explicit preferences fit when unresolved.
                if size_preference and size_preference != "WAIVE" and key not in (fit.get("nice_match") or []):
                    continue
                advantage = _quality_advantage(row, displaced)
                if not advantage:
                    continue
                proven.append({"canonical_facility_id": _identity(row), "facility_name": row.get("facility_name"),
                               "quality_advantage": advantage, "remaining_preference_matches": sorted(remaining),
                               "unresolved_preferences": list(fit.get("nice_unknown") or []),
                               "entrance_fee": row.get("entrance_fee"),
                               "synthetic_pilot": row.get("synthetic_pilot") is True})
            if len(proven) < 2:
                continue
            suggestions.append({"parameter": key, "authority": "PREFERENCE",
                                "action": "OFFER_PREFERENCE_ALTERNATIVE", "alternative_value": label,
                                "label": diagnostic["label"],
                                "change_kind": "WAIVE_NTH" if size_preference == "WAIVE" or not size_preference else "PROFILE_PATCH",
                                "acceptance": acceptance_for(key, intent, profile) if size_preference == "WAIVE" or not size_preference else None,
                                "profile_patch": patch, "new_recommendation_count": len(proven),
                                "additional_eligible_count": 0, "candidates": proven,
                                "requires_client_approval": True, "may_auto_change": False,
                                "basis": "SAME_COMPARATOR_FULL_ELIGIBLE_UNIVERSE",
                                "message": f"If you are comfortable with {label.lower()}, {len(proven)} additional communities enter the first {window} recommendations. They meet the verified requirements and the other explicit preferences; their quality evidence is shown below. They were already eligible, rather than excluded."})
        diagnostic["status"] = "MEASURED_ALTERNATIVES" if any(s["parameter"] == key for s in suggestions) else "NO_PROVEN_MINIMUM_TWO"
    # Open-ended NTHs are included in the advisor's evidence discussion. They do
    # not currently enter the deterministic comparator; removing one therefore
    # cannot promise a ranking gain. Unknown remains a research item, not a loss.
    for preference in (dynamic_preferences or {}).get("preferences") or []:
        if preference.get("importance", "NICE") != "NICE":
            continue
        pref_id = str(preference.get("preference_id") or "")
        if not pref_id:
            continue
        def status(row: dict) -> str:
            return next((str(a.get("status") or "UNKNOWN") for a in (row.get("dynamic_preference_fit") or {}).get("assessments") or []
                         if a.get("preference_id") == pref_id), "UNKNOWN")
        parameters.append({"parameter": pref_id, "label": str(preference.get("client_expression") or "Your stated preference"),
                           "excluded_by_preference_count": 0, "verified_mismatch_count": sum(status(r) == "MISMATCH" for r in eligible),
                           "unknown_count": sum(status(r) not in {"MATCH", "MISMATCH", "NOT_APPLICABLE"} for r in eligible),
                           "eligible_below_display_count": sum(status(r) == "MISMATCH" and _identity(r) not in baseline_ids for r in eligible),
                           "new_recommendation_count": 0, "status": "NO_VERIFIED_RANKING_EFFECT"})
    suggestions.sort(key=lambda item: (-item["new_recommendation_count"], item["parameter"], item["alternative_value"]))
    parameters.sort(key=lambda item: (-item["new_recommendation_count"], item["parameter"]))
    return {"status": "MEASURED_PREFERENCE_SENSITIVITY", "eligible_candidate_count": len(eligible),
            "display_limit": window, "profile_mutated": False, "parameters": parameters, "suggestions": suggestions,
            "ignored_neutral_parameters": ignored_neutral}

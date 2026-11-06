"""Narrow, evidence-based declaration for the November UNKNOWN repair.

This is not a blanket parity waiver. It accepts only the fixed
budget_medicaid_pending fixture's established transition away from an
unverified transportation MATCH, and only if candidate IDs, ranking and
overall match scores are exactly preserved. Every unrelated diff still fails.
"""
from __future__ import annotations

import re

_FIELDS = {
    "client_intent_fit.relevant_evidence_known_count",
    "matched_needs",
    "domain_breakdown.clinical_care_fit",
    "domain_breakdown.personal_social_fit",
    "evidence_certainty",
    "evidence_confidence",
    "explanation.capability_depth.unknown",
    "explanation.client_intent_fit.relevant_evidence_known_count",
    "explanation.practical_fit.known",
    "explanation.practical_fit.unknown",
    "explanation.unknown_tie_break_dimensions",
    "explanation.why_matches",
    "parameter_badges",
    "practical_fit_score",
    "preference_matches",
    "ranking_basis.verified_evidence_items",
    "tie_break_explanation_vs_next.comparison_evidence.higher_comparable_value",
    "tie_break_explanation_vs_next.comparison_evidence.lower_comparable_value",
    "tie_break_decisions[*].comparison_evidence.higher_comparable_value",
    "tie_break_decisions[*].comparison_evidence.lower_comparable_value",
}
_ROOTS = (
    re.compile(r"^\$\.(?:run_limit5|run_limit50|http_recommendations\.body)\."),
    re.compile(r"^\$\.db_side_effects\.decision_artifacts\[\d+\]\.payload_json\."),
)
_ITEM = re.compile(r"^(?:results|recommendation_audit_trace\.recommendations)\[\d+\]\.")
_INDEX = re.compile(r"\[\d+\]")


def _results(snapshot, path):
    obj = snapshot
    for key in path:
        obj = obj.get(key, {}) if isinstance(obj, dict) else {}
    return obj.get("results") or [] if isinstance(obj, dict) else []


def _ordered_ids(rows):
    return [str(row.get("canonical_facility_id")) for row in rows]


def _safe_transition(before, after):
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if before.get("canonical_facility_id") != after.get("canonical_facility_id"):
        return False
    for key in ("eligibility_status", "must_eligibility", "match_score", "rank_position"):
        if before.get(key) != after.get(key):
            return False
    old_matched = before.get("matched_needs") or []
    new_matched = after.get("matched_needs") or []
    old_ids = [r.get("parameter_id") for r in old_matched if isinstance(r, dict)]
    new_ids = [r.get("parameter_id") for r in new_matched if isinstance(r, dict)]
    if "transportation" not in old_ids or "transportation" in new_ids:
        return False
    if sorted(set(old_ids) - {"transportation"}) != sorted(new_ids):
        return False
    if len(old_ids) != len(new_ids) + 1:
        return False
    # Corrected evidence can lower confidence or become unscored; never improve it.
    for key in ("evidence_confidence", "practical_fit_score"):
        old, new = before.get(key), after.get(key)
        if isinstance(old, (int, float)) and isinstance(new, (int, float)) and new > old:
            return False
    return True


def _fixture_invariants(baseline, candidate):
    for path in (
        ("run_limit5",), ("run_limit50",), ("http_recommendations", "body"),
    ):
        before, after = _results(baseline, path), _results(candidate, path)
        if not before or _ordered_ids(before) != _ordered_ids(after):
            return False
        if not all(_safe_transition(a, b) for a, b in zip(before, after)):
            return False
    return True


def _allow_path(path, kind, old, new):
    name = path
    root_found = False
    for root in _ROOTS:
        match = root.match(name)
        if match:
            name = name[match.end():]
            root_found = True
            break
    if not root_found:
        return False
    # Strictly scoped to known recommendation fields and audit copies.
    item_match = _ITEM.match(name)
    if item_match:
        name = name[item_match.end():]
    name = _INDEX.sub("[*]", name)
    if name not in _FIELDS:
        return False
    if name.endswith("relevant_evidence_known_count"):
        return kind == "value" and isinstance(old, int) and isinstance(new, int) and new == old - 1
    if name in {"domain_breakdown.clinical_care_fit", "domain_breakdown.personal_social_fit", "practical_fit_score"}:
        return old == 0.0 and new is None and kind == "type float -> NoneType"
    if name == "evidence_confidence":
        return kind == "value" and isinstance(old, (int, float)) and isinstance(new, (int, float)) and new <= old
    if name == "matched_needs":
        return kind == "length 1 -> 0"
    if name in {"explanation.practical_fit.known", "explanation.why_matches", "parameter_badges", "preference_matches"}:
        return kind == "length 1 -> 0"
    if name in {"explanation.capability_depth.unknown"}:
        return kind == "length 1 -> 2"
    if name in {"explanation.practical_fit.unknown"}:
        return kind == "length 0 -> 1"
    if name in {"explanation.unknown_tie_break_dimensions"}:
        return kind == "length 4 -> 5"
    return kind == "value"


def approved_unknown_evidence_delta(case, baseline, candidate, diffs):
    """Return indexes that are proven intended; no blanket allowlisting."""
    if case != "budget_medicaid_pending" or not diffs:
        return set()
    if not _fixture_invariants(baseline, candidate):
        return set()
    if any(not _allow_path(path, kind, old, new) for path, kind, old, new in diffs):
        return set()
    return set(range(len(diffs)))

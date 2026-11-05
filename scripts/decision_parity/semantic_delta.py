"""Diagnostic-only, key-based interpretation of parity changes.

This never declares a difference acceptable and never changes parity exit status.
The goal is to distinguish real changes in ranked facilities from array reordering.
"""
from __future__ import annotations


def _by_id(rows):
    return {str(r.get("canonical_facility_id")): r for r in rows
            if isinstance(r, dict) and r.get("canonical_facility_id")}


def _statuses(row):
    fit = row.get("client_intent_fit") or {}
    return (
        row.get("eligibility_status"),
        row.get("must_eligibility"),
        tuple(sorted(fit.get("must_pass") or [])),
        tuple(sorted(fit.get("must_fail") or [])),
        tuple(sorted(fit.get("must_unknown") or [])),
        tuple(sorted(str(n.get("parameter_id")) for n in row.get("matched_needs") or [])),
        tuple(sorted(str(n.get("parameter_id")) for n in row.get("unknown_critical_needs") or [])),
    )


def report_semantic_delta(case: str, baseline: dict, candidate: dict) -> None:
    print(f"SEMANTIC_DELTA case={case}")
    for root in ("run_limit5", "run_limit50", "http_recommendations"):
        left = baseline.get(root) or {}
        right = candidate.get(root) or {}
        if root == "http_recommendations":
            left = left.get("body") or {}
            right = right.get("body") or {}
        a, b = left.get("results") or [], right.get("results") or []
        a_ids = [str(r.get("canonical_facility_id")) for r in a if isinstance(r, dict)]
        b_ids = [str(r.get("canonical_facility_id")) for r in b if isinstance(r, dict)]
        old, new = _by_id(a), _by_id(b)
        common = sorted(old.keys() & new.keys())
        changed = [fid for fid in common if _statuses(old[fid]) != _statuses(new[fid])]
        score_changed = [fid for fid in common if old[fid].get("match_score") != new[fid].get("match_score")]
        print(
            f"  {root}: length={len(a)}->{len(b)} "
            f"added={len(new.keys()-old.keys())} removed={len(old.keys()-new.keys())} "
            f"same_order={a_ids==b_ids} same_set={set(a_ids)==set(b_ids)} "
            f"eligibility_changed={len(changed)} match_score_changed={len(score_changed)}"
        )
        if changed:
            print(f"    eligibility_ids_sample={changed[:12]}")
        if score_changed:
            print(f"    score_ids_sample={score_changed[:12]}")
        if a_ids != b_ids:
            print(f"    top5_before={a_ids[:5]} top5_after={b_ids[:5]}")
    path = ("care_setting_policy", "decision_intelligence", "facility_selection_pipeline",
            "candidate_dispositions")
    def dispositions(snapshot):
        source = (snapshot.get("http_recommendations") or {}).get("body") or {}
        for key in path:
            source = source.get(key) if isinstance(source, dict) else None
        return source if isinstance(source, list) else []
    a, b = dispositions(baseline), dispositions(candidate)
    old, new = _by_id(a), _by_id(b)
    overlap = sorted(old.keys() & new.keys())
    semantic_changes = [fid for fid in overlap
                        if {k: v for k, v in old[fid].items() if k != "canonical_facility_id"}
                        != {k: v for k, v in new[fid].items() if k != "canonical_facility_id"}]
    print(
        f"  candidate_dispositions: count={len(a)}->{len(b)} "
        f"same_ids={set(old)==set(new)} "
        f"same_order={list(old)==list(new)} "
        f"changed_by_id={len(semantic_changes)}"
    )
    if semantic_changes:
        print(f"    disposition_changed_ids_sample={semantic_changes[:12]}")

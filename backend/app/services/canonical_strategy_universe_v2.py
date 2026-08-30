from __future__ import annotations

"""Deterministic candidate-universe selection from canonical V2 living strategy."""

from typing import Any, Dict, List, Sequence, Tuple


CANONICAL_STRATEGY_IDS = {
    "INDEPENDENT_LIVING",
    "INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE",
    "POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING",
    "ASSISTED_LIVING",
    "MEMORY_CARE",
    "SHORT_STAY_SKILLED_NURSING_REHAB",
    "LIFE_PLAN_CCRC",
    "LIFE_PLAN_CCRC_WITH_MEMORY_CONTINUUM",
}

_ACTIVE_STRATEGY_STATUSES = {"LEADING", "STRONG_OPTION", "VALID_OPTION"}


def _upper_set(values) -> set[str]:
    return {str(value or "").strip().upper() for value in values or [] if str(value or "").strip()}


def _candidate_supports(candidate: Dict[str, Any], strategy_id: str) -> bool:
    canonical_type = str(candidate.get("canonical_type") or "").strip().upper()
    modalities = _upper_set(candidate.get("housing_modalities") or [])
    all_modes = modalities | ({canonical_type} if canonical_type else set())

    if strategy_id in {"INDEPENDENT_LIVING", "INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE"}:
        return "INDEPENDENT_LIVING" in all_modes
    if strategy_id == "POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING":
        # Long-term destination must support IL. The rehab phase may be supplied by a
        # separate provider and is verified as a pathway later.
        return "INDEPENDENT_LIVING" in all_modes
    if strategy_id == "ASSISTED_LIVING":
        return bool(all_modes.intersection({"ASSISTED_LIVING", "ASSISTED_LIVING_RFG", "LIFE_PLAN_CCRC"}))
    if strategy_id == "MEMORY_CARE":
        return bool(all_modes.intersection({"MEMORY_CARE", "MEMORY_CARE_ONLY", "LOCKED_MEMORY_CARE_ONLY"}))
    if strategy_id == "SHORT_STAY_SKILLED_NURSING_REHAB":
        return "SKILLED_NURSING" in all_modes
    if strategy_id in {"LIFE_PLAN_CCRC", "LIFE_PLAN_CCRC_WITH_MEMORY_CONTINUUM"}:
        return any("CCRC" in value or "LIFE_PLAN" in value for value in all_modes)
    return False


def filter_universe_by_canonical_strategy_v2(
    rows: Sequence[Dict[str, Any]],
    client_state: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    strategies = [
        item
        for item in client_state.get("strategy_candidates") or []
        if isinstance(item, dict) and str(item.get("status") or "").strip().upper() in _ACTIVE_STRATEGY_STATUSES
    ]
    strategy_ids = [str(item.get("strategy_id") or "").strip().upper() for item in strategies]
    invalid = sorted({strategy_id for strategy_id in strategy_ids if strategy_id not in CANONICAL_STRATEGY_IDS})
    if invalid:
        raise RuntimeError("V2_NON_CANONICAL_STRATEGY_ID:" + ",".join(invalid))
    if not strategy_ids:
        raise RuntimeError("V2_NO_ACTIVE_CANONICAL_STRATEGY")

    selected = [row for row in rows if any(_candidate_supports(row, strategy_id) for strategy_id in strategy_ids)]
    if not selected:
        raise RuntimeError("V2_CANONICAL_STRATEGY_UNIVERSE_EMPTY")
    return selected, {
        "status": "CANONICAL_STRATEGY_SCOPED",
        "strategy_ids": strategy_ids,
        "market_universe_count": len(rows),
        "strategy_universe_count": len(selected),
        "rule": "Candidate inclusion is determined from canonical strategy IDs and canonical facility type/modalities only; raw client text is never parsed here.",
    }


__all__ = ["CANONICAL_STRATEGY_IDS", "filter_universe_by_canonical_strategy_v2"]

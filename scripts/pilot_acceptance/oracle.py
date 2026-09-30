"""Grade a decision against the pilot catalog, not against the engine's own verdict.

The engine already reports whether it thinks a facility fits. That report is exactly what
is under test, so nothing here reads it. Every recommendation is re-checked against the
community's own record: its price, the capabilities the family actually needs, what kind
of community it is, and whether it houses couples.
"""
from __future__ import annotations

import base64
import gzip
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_DIR = REPO_ROOT / "database" / "synthetic_pilot"

# Capabilities a client need can demand of a community, in the pilot's parameter naming.
CAPABILITY_PARAMETERS = (
    "adl_support", "medication_support", "memory_care", "dementia_alz_programs", "nursing_24_7",
    "transfer_assistance", "dialysis_arrangements", "respiratory_trach_vent", "wound_care",
    "pt", "ot", "speech_therapy", "skilled_nursing_capabilities", "transportation",
)


def _load(name: str) -> List[Dict[str, Any]]:
    raw = json.loads(gzip.decompress(base64.b64decode((PILOT_DIR / name).read_text(encoding="utf-8"))))
    if isinstance(raw, list):
        return raw
    return raw[next(key for key, value in raw.items() if isinstance(value, list))]


@lru_cache(maxsize=1)
def universe() -> Dict[str, Dict[str, Any]]:
    return {row["canonical_id"]: row for row in _load("facility_universe.json.gz.b64")}


@lru_cache(maxsize=1)
def facts() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in _load("facility_parameter_evidence.json.gz.b64"):
        out.setdefault(row["canonical_facility_id"], {})[row["parameter_id"]] = row.get("value")
    return out


def required_capabilities(profile: Dict[str, Any]) -> List[str]:
    """Capabilities the family's own profile says are required or high priority."""
    out = []
    for need in profile.get("needs") or []:
        if not isinstance(need, dict):
            continue
        parameter_id = str(need.get("parameter_id") or "")
        if parameter_id not in CAPABILITY_PARAMETERS:
            continue
        if str(need.get("requirement_level") or "").upper() not in {"REQUIRED", "HIGH"}:
            continue
        if str(need.get("desired_value") or "").upper() != "YES":
            continue
        out.append(parameter_id)
    return out


def stated_budget(profile: Dict[str, Any]) -> float | None:
    for need in profile.get("needs") or []:
        if isinstance(need, dict) and need.get("parameter_id") == "current_price":
            try:
                return float(need.get("desired_value"))
            except (TypeError, ValueError):
                return None
    return None


def grade(case: Dict[str, Any], profile: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    results = decision.get("results") or []
    budget = stated_budget(profile)
    needed = required_capabilities(profile)

    rows = []
    for item in results:
        facility_id = item.get("canonical_facility_id")
        record, evidence = universe().get(facility_id, {}), facts().get(facility_id, {})
        price = evidence.get("current_price")
        if case.get("requires_couple_accepting") and isinstance(price, (int, float)):
            fee = (record.get("pilot_service_evidence") or {}).get("second_resident_monthly_fee")
            price = price + fee if isinstance(fee, (int, float)) else None
        rows.append({
            "id": facility_id,
            "name": record.get("facility_name"),
            "archetype": record.get("synthetic_archetype"),
            "price": price,
            "accepts_couples": record.get("accepts_couples"),
            "rank": item.get("rank_display"),
            "over_budget": bool(budget and isinstance(price, (int, float)) and price > budget),
            "missing": [p for p in needed if str(evidence.get(p, "")).upper() != "YES"],
        })

    failures: List[str] = []

    for row in rows:
        if case.get("requires_couple_accepting") and row["price"] is None:
            failures.append(f"{row['id']} has no verified monthly total for two residents")
        if row["over_budget"]:
            failures.append(f"{row['id']} costs ${row['price']:,} against a ${budget:,.0f} budget")
        if row["missing"]:
            failures.append(f"{row['id']} does not provide {', '.join(row['missing'])}")

    never = set(case.get("never_archetypes") or ())
    for row in rows:
        if row["archetype"] in never:
            failures.append(f"{row['id']} is a {row['archetype']} community, which this case must never be shown")

    if case.get("expect_no_match"):
        if rows:
            failures.append(f"nothing in the market fits this budget, yet {len(rows)} communities were presented")
        if case.get("requires_market_coverage_notice") and not str(decision.get("market_coverage_notice") or "").strip():
            failures.append("no market-coverage notice explained why there is nothing to show")
    else:
        minimum = int(case.get("min_recommendations") or 0)
        if len(rows) < minimum:
            failures.append(f"expected at least {minimum} recommendation(s), got {len(rows)}")
        expected = set(case.get("any_of_archetypes") or ())
        if expected and rows and not any(row["archetype"] in expected for row in rows):
            failures.append(f"no recommendation is any of {sorted(expected)}; got {sorted({row['archetype'] for row in rows})}")
        if case.get("requires_couple_accepting"):
            refuses = [row["id"] for row in rows if row["accepts_couples"] is not True]
            if refuses:
                failures.append(f"couple case shown communities not recorded as housing couples: {', '.join(refuses)}")

    return {
        "budget": budget,
        "required_capabilities": needed,
        "recommendations": rows,
        "distinct_ranks": len({row["rank"] for row in rows}),
        "failures": failures,
        "passed": not failures,
    }

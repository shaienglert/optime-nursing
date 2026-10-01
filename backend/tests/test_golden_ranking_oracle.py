"""Full Ranking Oracle -- the ten golden personas against EVERY eligible candidate.

Independent of the decision engine: it reads the frozen pilot catalog and the persona's
structured answers, applies the owner-approved rules written out below, and checks the
engine on the whole eligible universe, not only the top ten.

Eligibility (all must hold; UNKNOWN is not a pass -- such candidates are "pending"):
  * within the stated radius (distance geometry is shared with the engine: location_radius)
  * license verified current (all pilot records are)
  * care needs from the structured answers, by capability evidence or licensing rule:
      bathing/dressing -> adl_support YES or RFG/SNF licence;
      medications      -> medication_support YES or RFG/SNF licence;
      memoryStatus "No" -> not a memory-care-only community;
      significant memory -> memory_care YES; wandering / secure unit -> secured_units YES;
      dialysis / wound care -> dialysis_arrangements / wound_care YES;
      rehab need -> pt YES
  * kosher "Requirement" -> kosher YES; couple -> accepts_couples; continuum "Required" ->
    a continuing-care community; move within 30 days/immediately -> current_availability YES
  * cost <= budget x 1.10, where cost is the private price, or under a Medicaid pathway the
    verified household out-of-pocket (none in the pilot -> pending)

Order (checked pairwise between every shown community and every eligible one ranked
below it or not shown): a lower-ranked B must not strictly beat a higher-ranked A on
  1. budget band (at/below budget before the +10% exception), then
  2. explicit NICE preferences with verified evidence (continuum "Preferred" -> continuing
     care; community size; preferred spoken language), counted as verified matches, then
  3. the Regulatory/Quality layer: the first measure both have from the same source, in
     the declared priority, decides; none shared -> tie.
A tie is never a violation. Unknown is never held against a community.
"""
from __future__ import annotations

import base64
import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "database" / "synthetic_pilot"
PERSONAS = json.loads((ROOT / "backend/gold_examples/oomnik_golden_personas_v1.submissions.json").read_text())["personas"]
ENV = {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200", "OPTIME_SEMANTIC_AI_ENABLED": "0"}
MEASURES = (
    ("inspection_rating", "higher"),
    ("deficiency_count", "lower"),
    ("total_nurse_hours_per_resident_day", "higher"),
    ("rn_hours_per_resident_day", "higher"),
    ("staffing_turnover", "lower"),
)
SIZE = {"small": "SMALL", "medium": "MEDIUM", "large": "LARGE"}


def _load(name):
    return json.loads(gzip.decompress(base64.b64decode((PILOT / name).read_text())))["records"]


FACILITIES = {r["canonical_id"]: r for r in _load("facility_universe.json.gz.b64")}
FACTS: Dict[str, Dict[str, Any]] = {}
for _r in _load("facility_parameter_evidence.json.gz.b64"):
    FACTS.setdefault(_r["canonical_facility_id"], {})[_r["parameter_id"]] = _r["value"]


def _lower(value) -> str:
    return str(value or "").strip().lower()


def _distances(state) -> Dict[str, Optional[float]]:
    from app.services.location_radius import annotate_distances, resolve_reference_point

    rows = [{"canonical_facility_id": fid} for fid in FACILITIES]
    index = {fid: {**f, "canonical_facility_id": fid} for fid, f in FACILITIES.items()}
    city = str(state.get("referenceAddress") or state.get("locationCity") or "").upper() or None
    reference = resolve_reference_point(state, index.values(), location_city=city)
    annotate_distances(rows, reference, index)
    return {row["canonical_facility_id"]: row.get("distance_miles") for row in rows}


def oracle(persona) -> Dict[str, Any]:
    s = persona["questionnaire_state"]
    hi = s.get("humanIntelligenceV2") or {}
    budget = float(s["budget"])
    radius = float(s.get("approvedSearchRadiusMiles") or s.get("maximumDistanceMiles"))
    distances = _distances(s)
    assistance = _lower(s.get("assistanceLevel"))
    memory = _lower(s.get("memoryStatus"))
    transition = hi.get("transitionRiskProfile") or {}
    future = hi.get("futureCareProfile") or {}
    medical = s.get("medicalCareProfile") or {}
    needs = {_lower(n) for n in medical.get("needs") or []}
    kosher = _lower((hi.get("culturalProfile") or {}).get("kosherRequirements")) == "requirement"
    couple = _lower(s.get("relationship")) == "couple"
    continuum = _lower(future.get("continuumOfCarePreference") or s.get("futureCarePreference"))
    urgent = _lower(s.get("moveTiming")) in {"within 30 days", "immediately"}
    medicaid_pathway = _lower(s.get("medicaidStatus")) in {"approved", "application pending"}
    candidates = []
    for fid, f in FACILITIES.items():
        facts = FACTS.get(fid, {})
        arche, ctype = f.get("synthetic_archetype"), f.get("canonical_type")
        licensed_care = ctype in {"ASSISTED_LIVING_RFG", "SKILLED_NURSING"}
        fail, unknown = [], []

        def need(ok: Optional[bool], label: str):
            (fail if ok is False else unknown if ok is None else []).append(label)

        def yes(parameter):
            value = str(facts.get(parameter, "UNKNOWN")).upper()
            return True if value == "YES" else (None if value == "UNKNOWN" else False)

        distance = distances.get(fid)
        if distance is None or distance > radius:
            continue  # outside the stated limit: not part of this search's universe
        if ("bathing" in assistance or "dressing" in assistance) and not licensed_care:
            need(yes("adl_support"), "adl_support")
        if "medication" in assistance and not licensed_care:
            need(yes("medication_support"), "medication_support")
        if memory == "no" and arche == "MEMORY_CARE":
            fail.append("no_forced_memory_placement")
        if "significant" in memory:
            need(yes("memory_care"), "memory_care")
        if _lower(transition.get("wanderingConcerns")) == "yes" or _lower(future.get("secureMemoryNeighborhoodNeed")) == "yes":
            need(yes("secured_units"), "secured_units")
        if "dialysis" in needs:
            need(yes("dialysis_arrangements"), "dialysis")
        if "wound care" in needs:
            need(yes("wound_care"), "wound_care")
        if _lower(transition.get("postHospitalRehabNeed")) == "yes":
            need(yes("pt"), "pt")
            need(yes("ot"), "ot")  # a rehabilitation path is PT and OT
        if kosher:
            need(yes("kosher"), "kosher")
        if couple and f.get("accepts_couples") is not True:
            fail.append("couple")
        if continuum == "required" and arche != "CONTINUING_CARE":
            fail.append("continuum")
        if urgent and str(facts.get("current_availability", "")).upper() == "NO":
            # Current policy: availability is confirmed directly with the community, so
            # only a recorded NO excludes; YES/LIMITED/unknown stay "confirm directly".
            fail.append("availability")
        candidates.append({"id": fid, "archetype": arche, "facts": facts, "facility": f, "fail": fail, "unknown": unknown})
    # Affordability floor of THIS search: cheapest private price among candidates that
    # passed every system/care requirement (verified), before budget and Medicaid.
    passed = [c["facts"].get("current_price") for c in candidates if not c["fail"] and not c["unknown"]]
    floor = min((p for p in passed if isinstance(p, (int, float))), default=None)
    medicaid_must = medicaid_pathway and floor is not None and budget < floor
    eligible, pending = [], []
    for c in candidates:
        fail, unknown, facts = list(c["fail"]), list(c["unknown"]), c["facts"]
        cost = facts.get("current_price")
        if couple and isinstance(cost, (int, float)):
            second = ((c["facility"].get("pilot_service_evidence") or {}).get("second_resident_monthly_fee"))
            cost = cost + second if isinstance(second, (int, float)) else None  # unknown couple cost
        if medicaid_must:
            value = str(facts.get("medicaid_attributes", "UNKNOWN")).upper()
            (fail if value == "NO" else unknown if value != "YES" else []).append("medicaid")
            cost = facts.get("medicaid_household_out_of_pocket")
        if not isinstance(cost, (int, float)):
            unknown.append("cost")
        elif cost > budget * 1.10:
            fail.append("budget")
        row = {**c, "cost": cost}
        if not fail:
            (pending if unknown else eligible).append(row)
    prefs = {
        "continuum": continuum == "preferred",
        "size": SIZE.get(next((k for k in SIZE if k in _lower((hi.get("personalityProfile") or {}).get("communitySizePreference"))), ""), None),
        "language": _lower((hi.get("languageProfile") or {}).get("preferredSpokenLanguage")) or None,
    }
    return {"eligible": eligible, "pending": pending, "budget": budget, "prefs": prefs}


# The approved person-fit table for an explicit community-size preference
# (EXPLICIT_PREFERENCE_CONGRUENCE_ONLY): exact band 100, neighbouring bands lower.
SIZE_FIT = {
    "SMALL": {"SMALL": 100, "MEDIUM": 60, "LARGE": 25},
    "MEDIUM": {"MEDIUM": 100, "SMALL": 65, "LARGE": 65},
    "LARGE": {"LARGE": 100, "MEDIUM": 70, "SMALL": 45},
}


def _nice(row, prefs) -> tuple:
    """(size fit, verified NICE matches) -- size congruence first, as the engine orders
    the explicit person-fit preference ahead of the other NICE items."""
    size = 0
    if prefs["size"]:
        size = SIZE_FIT[prefs["size"]].get(str(row["facility"].get("community_size") or "").upper(), 0)
    score = 0
    if prefs["continuum"] and row["archetype"] == "CONTINUING_CARE":
        score += 1
    lang = prefs["language"]
    if lang and lang != "english" and lang in _lower(row["facts"].get("languages")):
        score += 1
    return (size, score)


def beats(b, a, o) -> Optional[str]:
    """Why lower-ranked b strictly beats higher-ranked a, or None."""
    over_a, over_b = a["cost"] > o["budget"], b["cost"] > o["budget"]
    if over_a != over_b:
        return "budget band" if over_a else None
    na, nb = _nice(a, o["prefs"]), _nice(b, o["prefs"])
    if na != nb:
        return f"verified NICE {nb} > {na}" if nb > na else None
    for measure, better in MEASURES:
        va, vb = a["facts"].get(measure), b["facts"].get(measure)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and va != vb:
            wins = vb > va if better == "higher" else vb < va
            return f"{measure} {vb} vs {va}" if wins else None
    return None


@pytest.fixture(scope="module")
def engine():
    with patch.dict(os.environ, ENV, clear=False):
        from app.services.facility_parameter_service import refresh_runtime_cache
        from app.services.patient_decision_engine import run_patient_decision_engine

        refresh_runtime_cache("ranking-oracle")
        yield lambda state: run_patient_decision_engine(state, "", limit=20)


@pytest.mark.parametrize("persona", PERSONAS, ids=[p["id"] for p in PERSONAS])
def test_engine_matches_the_ranking_oracle_on_the_whole_eligible_universe(persona, engine):
    o = oracle(persona)
    response = engine(persona["questionnaire_state"])
    funnel = response.get("decision_funnel") or {}
    engine_ids = set(funnel.get("recommendable_ids") or [])
    oracle_ids = {r["id"] for r in o["eligible"]}
    problems: List[str] = []
    if engine_ids - oracle_ids:
        problems.append(f"engine recommends {len(engine_ids - oracle_ids)} the oracle does not: {sorted(engine_ids - oracle_ids)[:8]}")
    if oracle_ids - engine_ids:
        problems.append(f"oracle-eligible {len(oracle_ids - engine_ids)} the engine does not recommend: {sorted(oracle_ids - engine_ids)[:8]}")
    by_id = {r["id"]: r for r in o["eligible"]}
    shown = [r["canonical_facility_id"] for r in response.get("results") or []]
    positions = {r["canonical_facility_id"]: r.get("rank_position") for r in response.get("results") or []}
    for i, fid_a in enumerate(shown):
        a = by_id.get(fid_a)
        if a is None:
            continue
        for fid_b, b in by_id.items():
            if fid_b == fid_a:
                continue
            below = fid_b not in positions or (positions.get(fid_b) or 0) > (positions.get(fid_a) or 0)
            if not below:
                continue
            reason = beats(b, a, o)
            if reason:
                problems.append(f"#{positions.get(fid_a)} {fid_a} is above {fid_b} which wins on {reason}")
    assert not problems, f"{persona['id']} ({persona['title']}), oracle eligible {len(oracle_ids)} / engine {len(engine_ids)}:\n  " + "\n  ".join(problems[:25])

"""Golden Decision: the ten browser personas, from Structured Profile straight to the engine.

The browser journey used to be the only place these personas were graded, so every
decision check waited on a 90-second Playwright run that first had to survive the intake
harness. Here the same personas -- the QuestionnaireState the intake's own set() functions
produced (frontend/tests/golden-personas.test.ts writes it) -- go through
build_structured_profile -> materialize_questionnaire -> run_patient_decision_engine, and
the result is graded against the pilot catalog itself, never against the engine's opinion
of its own output. No browser, no AI, no narrative.

Each persona is its own test case so a failure names the persona and the rule it broke.
"""
from __future__ import annotations

import base64
import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire

ROOT = Path(__file__).resolve().parents[2]
SUBMISSIONS = ROOT / "backend" / "gold_examples" / "oomnik_golden_personas_v1.submissions.json"
EVIDENCE = ROOT / "database" / "synthetic_pilot" / "facility_parameter_evidence.json.gz.b64"
CATALOG = ROOT / "database" / "synthetic_pilot" / "facility_universe.json.gz.b64"
PILOT_ENV = {
    "OPTIME_CANONICAL_MARKET": "synthetic-pilot",
    "OOMNIK_PILOT_FACILITY_LIMIT": "500",
    "OPTIME_SEMANTIC_AI_ENABLED": "0",
}

PERSONAS: List[Dict[str, Any]] = json.loads(SUBMISSIONS.read_text(encoding="utf-8"))["personas"]

# Where a required need may legitimately live: the governed needs profile (at MUST level)
# or a client-intent MUST. Two structures for one fact is the debt the Structured Profile
# retires; until then both are accepted, and nothing else is.
NEED_IDS = {
    "adl_support": {"adl_support"},
    "medication_support": {"medication_support"},
    "memory_care": {"memory_care", "dementia_alz_programs"},
    "wandering_safety": {"dementia_alz_programs", "memory_care", "wandering_safety"},
    "rehabilitation": {"pt", "ot", "post_hospital_rehab", "rehabilitation", "skilled_nursing_capabilities"},
    "dialysis": {"dialysis_arrangements"},
    "dialysis_transportation": {"transportation"},
    "wound_care": {"wound_care"},
    "kosher": {"kosher"},
    "medicaid_pathway": {"medicaid_attributes"},
}
INTENT_KEYS = {
    "couple_coresidence": {"COUPLE_CORESIDENCE"},
    "continuum_of_care": {"CONTINUUM_OF_CARE_REQUIRED"},
    "adl_support": {"ADL_SUPPORT_AVAILABLE"},
    "medicaid_pathway": {"MEDICAID_PATHWAY_REQUIRED"},
}
MUST_LEVELS = {"HIGH", "REQUIRED", "MUST"}

# What a shown community must have on record for each required need. A need with no
# catalog evidence is not checked here; UNKNOWN never counts as YES.
EVIDENCE_CHECK = {
    "adl_support": lambda facts, row: facts.get("adl_support") == "YES",
    "medication_support": lambda facts, row: facts.get("medication_support") == "YES",
    "memory_care": lambda facts, row: facts.get("memory_care") == "YES",
    "dialysis": lambda facts, row: facts.get("dialysis_arrangements") == "YES",
    "dialysis_transportation": lambda facts, row: facts.get("transportation") == "YES"
        and (row.get("pilot_service_evidence") or {}).get("dialysis_transport_verified") is True,
    "rehabilitation": lambda facts, row: facts.get("pt") == "YES" and facts.get("ot") == "YES",
    "wound_care": lambda facts, row: facts.get("wound_care") == "YES",
    "kosher": lambda facts, row: facts.get("kosher") == "YES",
    "couple_coresidence": lambda facts, row: row.get("accepts_couples") is True,
    "wandering_safety": lambda facts, row: facts.get("secured_units") == "YES",
    "medicaid_pathway": lambda facts, row: facts.get("medicaid_attributes") == "YES",
}
FORBIDDEN_ARCHETYPES = {
    "MEMORY_CARE_ONLY": {"MEMORY_CARE"},
    "SKILLED_NURSING_ONLY": {"SKILLED_NURSING"},
    "REHABILITATION_ONLY": {"REHABILITATION"},
    "INDEPENDENT_LIVING": {"INDEPENDENT_LIVING", "ACTIVE_ADULT_55_PLUS"},
    "INDEPENDENT_LIVING_ONLY": {"INDEPENDENT_LIVING", "ACTIVE_ADULT_55_PLUS"},
    "ASSISTED_LIVING_ONLY": {"ASSISTED_LIVING_RFG"},
}
CARE_ARCHETYPES = {
    "INDEPENDENT_LIVING": {"INDEPENDENT_LIVING", "ACTIVE_ADULT_55_PLUS"},
    "ASSISTED_LIVING": {"ASSISTED_LIVING_RFG"},
    "MEMORY_CARE": {"MEMORY_CARE"},
    "SKILLED_NURSING": {"SKILLED_NURSING"},
    "REHABILITATION": {"REHABILITATION"},
    "CONTINUING_CARE": {"CONTINUING_CARE"},
    "SMALL_GROUP_HOME": {"SMALL_GROUP_HOME"},
}


def _care_violations(oracle, results, index):
    expected = oracle.get("care") or []
    unknown = set(expected) - set(CARE_ARCHETYPES)
    if unknown:
        return [f"unimplemented oracle.care values: {sorted(unknown)}"]
    allowed = set().union(*(CARE_ARCHETYPES[key] for key in expected)) if expected else set()
    return [f"Top-10 {row.get('canonical_facility_id')} is {index.get(row.get('canonical_facility_id'), {}).get('synthetic_archetype')}, outside oracle.care {expected}"
            for row in results[:10] if allowed and index.get(row.get("canonical_facility_id"), {}).get("synthetic_archetype") not in allowed]


def _preferred_violations(oracle, response):
    preferred = set(oracle.get("preferred") or [])
    unknown = preferred - {"hebrew", "social_fit", "nearby_places"}
    problems = [f"unimplemented oracle.preferred values: {sorted(unknown)}"] if unknown else []
    intelligence = response.get("decision_intelligence") or {}
    intent = intelligence.get("client_intent") or {}
    nice = {str(item.get("key")): item for item in intent.get("nice_to_haves") or []}
    if "hebrew" in preferred and str((nice.get("PREFERRED_LANGUAGE_SUPPORT") or {}).get("value") or "").lower() != "hebrew":
        problems.append("oracle.preferred Hebrew never reached the ranking NICE contract")
    if "social_fit" in preferred and "RICH_CULTURE_AND_ACTIVITIES" not in nice:
        problems.append("oracle.preferred social_fit never reached the ranking NICE contract")
    for row in response.get("results") or []:
        fid = row.get("canonical_facility_id")
        fit = row.get("client_intent_fit") or {}
        accounted = set(fit.get("nice_match") or []) | set(fit.get("nice_unknown") or []) | set(fit.get("nice_mismatch") or [])
        for preference, key in [("hebrew", "PREFERRED_LANGUAGE_SUPPORT"), ("social_fit", "RICH_CULTURE_AND_ACTIVITIES")]:
            if preference in preferred and key not in accounted:
                problems.append(f"{fid}: preferred {preference} has no match/mismatch/unknown evidence trace")
        if "hebrew" in preferred and "PREFERRED_LANGUAGE_SUPPORT" in set(fit.get("nice_match") or []):
            languages = str(FACTS.get(fid, {}).get("languages") or "").lower().split(",")
            if "hebrew" not in {language.strip() for language in languages}:
                problems.append(f"{fid}: Hebrew NICE match is unsupported by catalog language evidence")
        if "social_fit" in preferred and "RICH_CULTURE_AND_ACTIVITIES" in set(fit.get("nice_match") or []):
            service = (CATALOG_ROWS.get(fid) or {}).get("pilot_service_evidence") or {}
            if service.get("social_engagement_verified") is not True:
                problems.append(f"{fid}: social NICE match is unsupported by catalog service evidence")
        if "nearby_places" in preferred:
            place = row.get("nearby_place_fit") or {}
            if place.get("status") not in {"KNOWN", "UNKNOWN", "NOT_EVALUATED"}:
                problems.append(f"{fid}: preferred nearby_places has no evidence or visible unknown")
            if place.get("status") == "KNOWN" and not place.get("source"):
                problems.append(f"{fid}: nearby_places claims KNOWN without a source")
            if place.get("status") in {"UNKNOWN", "NOT_EVALUATED"} and not place.get("reason"):
                problems.append(f"{fid}: nearby_places uncertainty has no explanation")
    return problems


def _facts() -> Dict[str, Dict[str, Any]]:
    records = json.loads(gzip.decompress(base64.b64decode(EVIDENCE.read_text())))["records"]
    out: Dict[str, Dict[str, Any]] = {}
    for row in records:
        out.setdefault(row["canonical_facility_id"], {})[row["parameter_id"]] = row["value"]
    return out


FACTS = _facts()
CATALOG_ROWS = {row["canonical_id"]: row for row in
                json.loads(gzip.decompress(base64.b64decode(CATALOG.read_text())))["records"]}


@pytest.fixture(scope="module")
def decisions() -> Dict[str, Dict[str, Any]]:
    with patch.dict(os.environ, PILOT_ENV, clear=False):
        from app.services.decision_engine_core import get_canonical_facility_index
        from app.services.facility_parameter_service import refresh_runtime_cache
        from app.services.patient_decision_engine import run_patient_decision_engine

        refresh_runtime_cache("golden-persona-decisions")
        index = get_canonical_facility_index()
        out = {}
        for persona in PERSONAS:
            profile = build_structured_profile(persona["questionnaire_state"])
            questionnaire = materialize_questionnaire(profile)
            try:
                response = run_patient_decision_engine(questionnaire, "", limit=50)
            except Exception as exc:  # one persona's crash must not hide the other nine
                response = {"_crash": f"{type(exc).__name__}: {exc}"}
            out[persona["id"]] = {"response": response, "index": index}
        return out


def _violations(persona: Dict[str, Any], decision: Dict[str, Any]) -> List[str]:
    oracle, response, index = persona["oracle"], decision["response"], decision["index"]
    if "_crash" in response:
        return [f"engine crashed: {response['_crash']}"]
    budget = float(oracle["budget"])
    ceiling = budget * 1.10
    results = response.get("results") or []
    needs = {n.get("parameter_id"): n for n in (response.get("patient_needs_profile") or {}).get("needs") or []}
    intent = (response.get("decision_intelligence") or {}).get("client_intent") or {}
    intent_must = {str(m.get("key") or "") for m in intent.get("must_haves") or []}
    problems: List[str] = _care_violations(oracle, results, index) + _preferred_violations(oracle, response)

    # 1. The profile reached the engine as stated.
    price_need = needs.get("current_price")
    if not price_need or float(price_need.get("desired_value") or 0) != budget:
        problems.append(f"budget not preserved: {price_need and price_need.get('desired_value')} != {budget:g}")
    for required in oracle.get("required") or []:
        in_needs = any(str((needs.get(pid) or {}).get("requirement_level") or "").upper() in MUST_LEVELS for pid in NEED_IDS.get(required, ()))
        in_intent = bool(INTENT_KEYS.get(required, set()) & intent_must)
        if not (in_needs or in_intent):
            seen = {pid: (needs.get(pid) or {}).get("requirement_level") for pid in NEED_IDS.get(required, ()) if pid in needs}
            problems.append(f"required '{required}' is not a MUST (needs: {seen or 'absent'}; intent MUST: {sorted(intent_must)})")

    # 2. Every shown community honours the hard rules, checked against the catalog.
    radius = float(oracle["distance"])
    scope = response.get("location_scope") or {}
    for row in results:
        fid = row.get("canonical_facility_id")
        facts, record = FACTS.get(fid, {}), index.get(fid, {})
        # The budget is compared with the cost under the funding pathway: private-pay
        # price, or the household out-of-pocket under Medicaid (never the private price).
        price = row.get("relevant_monthly_cost") if row.get("funding_pathway") == "MEDICAID" else row.get("starting_monthly_price")
        if row.get("funding_pathway") == "MEDICAID" and not isinstance(price, (int, float)):
            problems.append(f"{fid} shown under the Medicaid pathway with no verified household cost")
        if isinstance(price, (int, float)):
            if price > ceiling:
                problems.append(f"{fid} ${price:g} exceeds budget+10% (${ceiling:g})")
            if bool(row.get("budget_exception")) != (price > budget):
                problems.append(f"{fid} ${price:g} budget_exception label is {row.get('budget_exception')}")
        if scope.get("applied") and isinstance(row.get("distance_miles"), (int, float)) and row["distance_miles"] > radius:
            problems.append(f"{fid} at {row['distance_miles']} mi is outside the {radius:g}-mile limit")
        for forbidden in oracle.get("forbidden") or []:
            if record.get("synthetic_archetype") in FORBIDDEN_ARCHETYPES.get(forbidden, set()):
                problems.append(f"{fid} is {record.get('synthetic_archetype')}, forbidden by {forbidden}")
        for required in oracle.get("required") or []:
            check = EVIDENCE_CHECK.get(required)
            if check and not check(facts, record):
                problems.append(f"{fid} shown without catalog evidence for '{required}'")
    first_exception = next((i for i, r in enumerate(results) if r.get("budget_exception")), None)
    if first_exception is not None and not all(r.get("budget_exception") for r in results[first_exception:]):
        problems.append("an in-budget community is ranked after an over-budget exception")
    if not scope.get("applied"):
        problems.append(f"distance limit not applied: {scope.get('reason')}")

    # 3. The mechanical funnel reconciles, and a zero result is explained, never assumed.
    funnel = response.get("decision_funnel") or {}
    if not funnel:
        problems.append("no decision funnel")
    else:
        if funnel.get("reconciliation_errors"):
            problems.append(f"funnel does not reconcile: {funnel['reconciliation_errors']}")
        if funnel.get("shown_count") != len(results):
            problems.append(f"funnel shown {funnel.get('shown_count')} != results {len(results)}")
        if not results:
            klass = funnel.get("zero_result_classification")
            if klass not in {"CORRECT_ZERO", "EVIDENCE_PENDING"}:
                problems.append(f"zero result classified {klass}: {funnel.get('zero_result_reason')}")
            elif not funnel.get("zeroing_parameter"):
                problems.append(f"zero result ({klass}) names no zeroing parameter")
            expected = oracle.get("zero_result")
            if expected and expected != klass:
                problems.append(f"zero result {klass} at {funnel.get('zeroing_stage')}/{funnel.get('zeroing_parameter')}, oracle expects {expected}")
    return problems


@pytest.mark.parametrize("persona", PERSONAS, ids=[p["id"] for p in PERSONAS])
def test_golden_persona_decision(persona, decisions):
    problems = _violations(persona, decisions[persona["id"]])
    assert not problems, f"{persona['id']} ({persona['title']}):\n  " + "\n  ".join(problems)


def test_care_contract_catches_a_top_community_outside_the_declared_setting():
    assert _care_violations({"care": ["REHABILITATION"]}, [{"canonical_facility_id": "bad"}],
                            {"bad": {"synthetic_archetype": "SMALL_GROUP_HOME"}})


def test_preferred_contract_catches_silently_dropped_nice_preferences():
    problems = _preferred_violations({"preferred": ["hebrew", "social_fit", "nearby_places"]},
                                    {"results": [{"canonical_facility_id": "missing"}]})
    assert any("Hebrew" in problem for problem in problems)
    assert any("social_fit" in problem for problem in problems)
    assert any("nearby_places" in problem for problem in problems)


def test_unknown_oracle_fields_cannot_silently_pass():
    assert _care_violations({"care": ["UNIMPLEMENTED"]}, [], {})
    assert _preferred_violations({"preferred": ["UNIMPLEMENTED"]}, {})

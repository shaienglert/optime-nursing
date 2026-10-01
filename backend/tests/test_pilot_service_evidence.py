from pathlib import Path
import importlib.util

from app.services.governed_evidence_runtime import agent_and_provider_payloads, pilot_service_payload
from app.services.semantic_facility_requirements import _pilot_verifies_requirement, _row_verifies_future_care
from app.services.semantic_facility_requirements import _apply_pilot_monthly_cost, _row_verifies_budget
from app.services.living_strategy_runtime import build_living_strategy_context

spec = importlib.util.spec_from_file_location("pilot_builder", Path(__file__).resolve().parents[2] / "scripts/build_synthetic_pilot_facilities.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def candidate(index=27, archetype="ASSISTED_LIVING_RFG"):
    return {"canonical_facility_id": f"PILOT-NV-{index:03d}", "synthetic_pilot": True,
            "pilot_service_evidence": builder.pilot_service_evidence(index, archetype)}


def test_verified_pilot_medication_reaches_shared_gate():
    assert any(p.get("medication_support_verified") is True for p in agent_and_provider_payloads(candidate()))


def test_non_care_pilot_does_not_gain_medication_support():
    assert not any(p.get("medication_support_verified") is True for p in agent_and_provider_payloads(candidate(2, "INDEPENDENT_LIVING")))


def test_real_or_wrong_identity_cannot_use_pilot_proof():
    row = candidate()
    row["synthetic_pilot"] = False
    assert not pilot_service_payload(row)
    row["synthetic_pilot"] = True
    row["canonical_facility_id"] = "PILOT-NV-028"
    assert not pilot_service_payload(row)


def test_unverified_fixture_cannot_become_proof():
    row = candidate()
    row["pilot_service_evidence"]["verification_status"] = "UNVERIFIED"
    assert not pilot_service_payload(row)


def test_language_requirement_checks_actual_language():
    requirement = {"key": "SEMANTIC_LANGUAGE_SUPPORT"}
    assert _pilot_verifies_requirement(candidate(), requirement, {"preferredLanguage": "Hebrew"})
    assert not _pilot_verifies_requirement(candidate(), requirement, {"preferredLanguage": "French"})


def test_kosher_no_does_not_pass():
    assert _pilot_verifies_requirement(candidate(), {"key": "SEMANTIC_KOSHER_DIET"}, {})
    assert not _pilot_verifies_requirement(candidate(28), {"key": "SEMANTIC_KOSHER_DIET"}, {})


def test_clinical_requirements_must_all_be_supported():
    requirement = {"key": "SEMANTIC_CLINICAL_ACUITY", "reason": "Dialysis transport and daily wound care required"}
    assert _pilot_verifies_requirement(candidate(7, "CONTINUING_CARE"), requirement, {})
    assert not _pilot_verifies_requirement(candidate(), requirement, {})
    # Transport LIMITED cannot be treated as verified dialysis transport.
    assert not _pilot_verifies_requirement(candidate(6, "REHABILITATION"), requirement, {})
    assert not _pilot_verifies_requirement(candidate(7, "CONTINUING_CARE"), requirement,
        {"medicalCareProfile": {"dialysisFrequency": "5 times per week"}})


def test_continuum_same_evidence_rule_as_structured_gate():
    assert _row_verifies_future_care(candidate(7, "CONTINUING_CARE"))
    assert not _row_verifies_future_care(candidate(1, "INDEPENDENT_LIVING"))


def test_accessibility_does_not_prove_specific_route_distance():
    assert not _pilot_verifies_requirement(candidate(), {"key": "SEMANTIC_MOBILITY_LAYOUT", "reason": "Dining must be within 100 meters"}, {})


def test_denied_wandering_preserves_mild_memory_without_secure_gate():
    strategy = build_living_strategy_context({"memoryStatus": "Mild changes"}, "Dad forgets medication but has no wandering or secure-unit need. Not a locked memory unit.")
    assert strategy["signals"]["memory_care_needed"] is False


def test_positive_wandering_still_needs_memory_care():
    strategy = build_living_strategy_context({"memoryStatus": "Mild changes"}, "Dad has wandering and needs memory care.")
    assert strategy["signals"]["memory_care_needed"] is True


def test_couple_budget_uses_total_and_cost_application_is_idempotent():
    row = candidate()
    row.update(starting_monthly_price=7600, client_intent_fit={"must_pass": ["COUPLE_CORESIDENCE"]})
    _apply_pilot_monthly_cost(row)
    assert row["starting_monthly_price"] == 8350
    assert row["monthly_price_basis"] == "TWO_RESIDENT_TOTAL"
    assert _row_verifies_budget(row, {"budget": 8000})
    _apply_pilot_monthly_cost(row)
    assert row["starting_monthly_price"] == 8350
    assert row["single_resident_starting_monthly_price"] == 7600


def test_single_resident_price_and_real_facility_are_preserved():
    row = candidate()
    row["starting_monthly_price"] = 7600
    _apply_pilot_monthly_cost(row)
    assert row["starting_monthly_price"] == 7600
    assert row["monthly_price_basis"] == "SINGLE_RESIDENT"
    row["synthetic_pilot"] = False
    row["client_intent_fit"] = {"must_pass": ["COUPLE_CORESIDENCE"]}
    _apply_pilot_monthly_cost(row)
    assert row["starting_monthly_price"] == 7600


def test_unverified_couple_fee_is_not_invented():
    row = candidate(6)
    row.update(starting_monthly_price=6000, client_intent_fit={"must_unknown": ["COUPLE_CORESIDENCE"]})
    _apply_pilot_monthly_cost(row)
    assert row["starting_monthly_price"] == 6000
    assert "monthly_price_basis" not in row

"""Owner-approved care programs: category cannot replace verified evidence."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from scripts.pilot_acceptance.care_oracle import evaluate_care, evidence
from scripts.pilot_acceptance.oracle import universe
from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent
from app.services.governed_evidence_runtime import post_hospital_rehab_state


def full_program():
    return deepcopy(universe()["PILOT-NV-151"])


def test_building_category_does_not_change_program_proof():
    row = full_program()
    for category in ["SMALL_GROUP_HOME", "CONTINUING_CARE", "SKILLED_NURSING"]:
        row["synthetic_archetype"] = category
        assert evaluate_care(["REHABILITATION"], row)["state"] == "PASS"
    row["pilot_service_evidence"]["nursing_support_verified"] = False
    assert evaluate_care(["REHABILITATION"], row)["state"] == "FAIL"


@pytest.mark.parametrize("mutation", ["missing", "unverified", "conflict", "wrong_identity", "no"])
def test_program_evidence_cannot_be_guessed(mutation):
    row = full_program()
    parameters, provider_index = evidence()
    providers = deepcopy(provider_index[(row["canonical_id"], "continuum_rehabilitation")])
    if mutation == "missing":
        providers = []
    elif mutation == "unverified":
        providers[0]["verification_status"] = "UNVERIFIED"
    elif mutation == "conflict":
        providers[0]["conflict_status"] = "CONFLICT"
    elif mutation == "wrong_identity":
        providers[0]["canonical_facility_id"] = "OTHER"
    else:
        providers[0]["value"] = "NO"
    assert evaluate_care(["REHABILITATION"], row, parameters, providers)["state"] == ("FAIL" if mutation == "no" else "UNKNOWN")


def test_post_hospital_need_has_a_separate_gate_from_outpatient_therapy():
    state = {"humanIntelligenceV2": {"transitionRiskProfile": {"postHospitalRehabNeed": "Yes"}}}
    intent = build_client_intent(state, "", {}, {})
    assert "POST_HOSPITAL_REHAB_PROGRAM" in {x["key"] for x in intent["must_haves"]}
    assert "POST_HOSPITAL_REHAB_PROGRAM" not in {x["key"] for x in build_client_intent({}, "", {}, {})["must_haves"]}


def test_pt_ot_and_skilled_label_do_not_prove_clinical_program():
    row = {"canonical_type": "SKILLED_NURSING", "agent_person_fit_evidence": [
        {"source": "OFFICIAL_PROVIDER_WEBSITE", "payload": {"official_identity_verified": True, "pt_ot_verified": True}}]}
    assert post_hospital_rehab_state(row) == "UNKNOWN"
    gate = evaluate_candidate_intent(row, {"must_haves": [{"key": "POST_HOSPITAL_REHAB_PROGRAM"}]})
    assert "POST_HOSPITAL_REHAB_PROGRAM" in gate["must_unknown"]


def test_real_program_requires_trusted_identity_and_complete_clinical_evidence():
    payload = {k: True for k in ["official_identity_verified", "post_hospital_rehab_program_verified",
                                "pt_ot_verified", "nursing_support_verified", "physician_coordination_verified"]}
    row = {"agent_person_fit_evidence": [{"source": "OFFICIAL_PROVIDER_WEBSITE", "payload": payload}]}
    assert post_hospital_rehab_state(row) == "PASS"
    payload["official_identity_verified"] = False
    assert post_hospital_rehab_state(row) == "UNKNOWN"


def test_unknown_acceptance_path_cannot_pass_even_without_results():
    from scripts.pilot_acceptance.oracle import grade
    report = grade({"any_of_care_paths": {"UNIMPLEMENTED"}, "expect_no_match": True}, {}, {"results": []})
    assert not report["passed"]


def test_service_evidence_is_bound_to_fictional_provenance_and_source():
    row = full_program()
    row["pilot_service_evidence"]["provenance"]["not_real_world_evidence"] = False
    assert evaluate_care(["REHABILITATION"], row)["state"] == "UNKNOWN"


def test_pilot_program_cannot_pass_when_provider_program_proof_is_missing():
    row = full_program()
    row["canonical_facility_id"] = row["canonical_id"]
    parameters, _ = evidence()
    row["verified_capabilities"] = {
        key: parameters[(row["canonical_id"], key)][0]["value"]
        for key in ("pt", "ot", "therapy_staffing", "nursing_24_7")
    }
    assert post_hospital_rehab_state(row) == "PASS"
    with patch("app.services.governed_evidence_runtime._pilot_rehabilitation_programs", return_value={}):
        assert post_hospital_rehab_state(row) == "UNKNOWN"

"""Every structured assistance label creates exactly the needs its contract names.

Owner decision: an assistance level never infers transfer help, medication support or
specialist/around-the-clock nursing that the family did not select.
"""
import pytest

from app.services.decision_engine_core import build_patient_needs_profile
from app.services.structured_intake_mapping import STRUCTURED_INTAKE_MAPPING_CONTRACT

_ASSISTANCE_PARAMETERS = {"adl_support", "medication_support", "transfer_assistance", "skilled_nursing_capabilities", "nursing_24_7"}
_LABELS = list(STRUCTURED_INTAKE_MAPPING_CONTRACT["assistanceLevel"].items())


def _needs(state):
    return {row["parameter_id"] for row in build_patient_needs_profile(state, "")["needs"]}


@pytest.mark.parametrize("label,contract", _LABELS)
def test_engine_needs_equal_contract_parameters_for_every_label(label, contract):
    assert _needs({"assistanceLevel": label}) & _ASSISTANCE_PARAMETERS == set(contract["parameter_ids"])


@pytest.mark.parametrize("label", ["Light assistance", "Help with toileting", "Daytime supervision", "24/7 support required"])
def test_general_assistance_never_infers_transfer_help(label):
    assert "transfer_assistance" not in _needs({"assistanceLevel": label})


def test_skilled_nursing_label_is_not_round_the_clock_nursing():
    needs = _needs({"assistanceLevel": "Skilled nursing care"})
    assert "skilled_nursing_capabilities" in needs and "nursing_24_7" not in needs


def test_explicit_transfer_method_creates_the_transfer_need():
    for method in ("One person", "Two people", "Mechanical lift"):
        state = {"assistanceLevel": "Light assistance", "medicalCareProfile": {"transferAssistance": method}}
        assert "transfer_assistance" in _needs(state)


@pytest.mark.parametrize("falls", ["One", "More than one"])
def test_falls_alone_add_no_service_need(falls):
    state = {"medicalCareProfile": {"recentFalls": falls}}
    assert _needs(state) & _ASSISTANCE_PARAMETERS == set()

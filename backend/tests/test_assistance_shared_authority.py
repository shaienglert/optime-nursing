import pytest
from app.services.structured_intake_mapping import STRUCTURED_INTAKE_MAPPING_CONTRACT, assistance_parameters
from app.services.living_strategy_runtime import build_living_strategy_context
from app.services.client_intent_runtime import build_client_intent


@pytest.mark.parametrize("selection,contract", list(STRUCTURED_INTAKE_MAPPING_CONTRACT["assistanceLevel"].items()))
def test_each_structured_assistance_choice_reaches_same_adl_gate(selection, contract):
    state = {"assistanceLevel": selection}
    strategy = build_living_strategy_context(state, "")
    intent = build_client_intent(state, "", strategy, {})
    expected = "adl_support" in contract["parameter_ids"]
    assert strategy["signals"]["adl_support_needed"] is expected
    assert ("ADL_SUPPORT_AVAILABLE" in {r["key"] for r in intent["must_haves"]}) is expected


def test_joined_and_list_storage_preserve_all_selected_parameters():
    selections = ["Help with medications", "Help with toileting"]
    assert assistance_parameters(selections) == assistance_parameters(", ".join(selections)) == {
        "medication_support", "adl_support", "transfer_assistance"}

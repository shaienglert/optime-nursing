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


@pytest.mark.parametrize("selection", ["Help with bathing", "Help with dressing", "Help with toileting", "Daytime supervision", "24/7 support required"])
def test_adding_assistance_preserves_existing_medication_need_and_must(selection):
    from app.services.decision_engine_core import build_patient_needs_profile
    state = {"assistanceLevel": f"Help with medications, {selection}"}
    needs = {r['parameter_id'] for r in build_patient_needs_profile(state, '')['needs']}
    strategy = build_living_strategy_context(state, '')
    intent = build_client_intent(state, '', strategy, {})
    must = {r['key'] for r in intent['must_haves']}
    assert {'medication_support', 'adl_support'} <= needs
    assert {'MEDICATION_SUPPORT_AVAILABLE', 'ADL_SUPPORT_AVAILABLE'} <= must


@pytest.mark.parametrize("selection", ["Help with bathing", "Help with dressing", "Help with toileting", "Daytime supervision", "24/7 support required"])
def test_replacing_medication_answer_does_not_keep_withdrawn_medication_requirement(selection):
    from app.services.decision_engine_core import build_patient_needs_profile
    state = {"assistanceLevel": selection}
    needs = {r['parameter_id'] for r in build_patient_needs_profile(state, '')['needs']}
    intent = build_client_intent(state, '', build_living_strategy_context(state, ''), {})
    must = {r['key'] for r in intent['must_haves']}
    assert 'medication_support' not in needs
    assert 'MEDICATION_SUPPORT_AVAILABLE' not in must
    assert 'adl_support' in needs
    assert 'ADL_SUPPORT_AVAILABLE' in must


def test_same_order_is_not_evidence_that_an_adl_answer_was_ignored():
    from app.services.client_intent_runtime import evaluate_candidate_intent, intent_rank_key
    state = {'assistanceLevel': 'Help with toileting'}
    intent = build_client_intent(state, '', build_living_strategy_context(state, ''), {})
    candidates = [{'canonical_facility_id': name, 'canonical_type': 'INDEPENDENT_LIVING',
                   'verified_capabilities': {'adl_support': 'YES'}} for name in ['a', 'b']]
    fits = [evaluate_candidate_intent(row, intent) for row in candidates]
    assert all('ADL_SUPPORT_AVAILABLE' in fit['must_pass'] for fit in fits)
    assert intent_rank_key({'client_intent_fit': fits[0]}) == intent_rank_key({'client_intent_fit': fits[1]})
    unknown = evaluate_candidate_intent({'canonical_type': 'INDEPENDENT_LIVING'}, intent)
    assert 'ADL_SUPPORT_AVAILABLE' in unknown['must_unknown']

from copy import deepcopy
from unittest.mock import patch

import pytest

from app.services import intake_interpretation as facts
from app.services import patient_decision_engine_runtime as runtime
from app.services.client_intent_runtime import build_client_intent
from app.services.living_strategy_runtime import build_living_strategy_context
from app.services.human_intelligence_runtime import build_human_intelligence_context


def test_one_extraction_feeds_all_projections(monkeypatch):
    monkeypatch.setenv('OPTIME_SEMANTIC_AI_ENABLED', '0')
    monkeypatch.setenv('OPTIME_SEMANTIC_AI_REQUIRED', '0')
    with patch.object(facts, 'extract_intake_facts', wraps=facts.extract_intake_facts) as extract:
        profile = runtime.build_patient_needs_profile({'budget': 7000}, 'Mother needs bathing and medication reminders in Las Vegas.')
    assert extract.call_count == 1
    facts.validate_interpretation(profile)
    assert profile['interpretation_id']
    assert profile['living_strategy']['signals']['medication_support_needed']
    assert profile['care_delivery_signals']['medication_support_needed']


def test_consumers_do_not_reinterpret_changed_raw_text():
    record = facts.extract_intake_facts({'budget': 8000}, 'Both parents want to live together in Las Vegas. Neither has dementia. Father needs bathing help.')
    with patch.object(facts, 'extract_intake_facts', side_effect=AssertionError('consumer reinterpreted')):
        strategy = build_living_strategy_context({}, 'dementia unrelated injected story', intake_facts=record)
        human = build_human_intelligence_context({}, 'recently widowed', intake_facts=record)
        intent = build_client_intent({}, 'outside Las Vegas', strategy, human, intake_facts=record)
    assert strategy['household']['type'] == 'COUPLE'
    assert strategy['signals']['memory_care_needed'] is False
    assert human['signals']['recent_bereavement']['value'] == 'UNKNOWN'
    keys = {m['key'] for m in intent['must_haves']}
    assert {'COUPLE_CORESIDENCE', 'ADL_SUPPORT_AVAILABLE', 'LAS_VEGAS'} <= keys
    assert 'SECURE_MEMORY_CARE_CONFIRMED' not in keys


@pytest.mark.parametrize('story,state,parameter', [
    ('Father needs pills reminders.', {'medicalCareProfile': {'needs': ['Medication management']}}, 'medication_support'),
    ('Mother needs assistance with daily activities.', {}, 'adl_support'),
    ('Father needs help bathing.', {}, 'adl_support'),
])
def test_care_fact_cannot_disagree_between_clinical_strategy_and_delivery(story, state, parameter):
    record = facts.extract_intake_facts(state, story)
    positive = any(n['parameter_id'] == parameter and n['desired_value'] == 'YES' for n in record['clinical_profile']['needs'])
    key = 'adl' if parameter == 'adl_support' else 'medication'
    assert record['strategy'][key] == positive
    assert record['delivery'][key + '_support_needed'] == positive


def test_unknown_is_not_a_negative_fact():
    record = facts.extract_intake_facts({}, '')
    assert record['clinical_profile']['needs'] == []
    assert record['human']['recent_bereavement']['value'] == 'UNKNOWN'


@pytest.mark.parametrize('mutation', ['needs', 'client_intent', 'record'])
def test_changed_confirmed_projection_is_rejected(monkeypatch, mutation):
    monkeypatch.setenv('OPTIME_SEMANTIC_AI_ENABLED', '0')
    profile = runtime.build_patient_needs_profile({}, 'Mother needs help bathing in Las Vegas.')
    original = deepcopy(profile)
    if mutation == 'record':
        profile['intake_interpretation']['source_digest'] = 'changed'
    elif mutation == 'needs':
        profile['needs'].clear()
    else:
        profile['client_intent']['must_haves'].clear()
    with pytest.raises(ValueError, match='INTAKE_INTERPRETATION_'):
        facts.validate_interpretation(profile)
    facts.validate_interpretation(original)


def test_intent_uses_budget_from_same_record_not_second_state():
    record = facts.extract_intake_facts({'budget': 8000}, 'Mother needs bathing help in Las Vegas.')
    strategy = build_living_strategy_context({}, intake_facts=record)
    intent = build_client_intent({'budget': 0}, '', strategy, {}, intake_facts=record)
    assert 'BUDGET_FIT' in {n['key'] for n in intent['nice_to_haves']}

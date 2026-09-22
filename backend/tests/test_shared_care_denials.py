from unittest.mock import patch

import pytest

from app.services import care_input_assertions as assertions
from app.services.patient_decision_engine_runtime import build_patient_needs_profile


@pytest.fixture(autouse=True)
def deterministic_intake(monkeypatch):
    monkeypatch.setenv('OPTIME_SEMANTIC_AI_ENABLED', '0')
    monkeypatch.setenv('OPTIME_SEMANTIC_AI_REQUIRED', '0')


def musts(profile):
    return {item['key'] for item in profile['client_intent']['must_haves']}


def test_one_explicit_denial_is_shared_by_every_care_layer():
    story = 'She is fully independent and does not need medication support or help with bathing or dressing.'
    with patch.object(assertions, 'extract_care_denials', wraps=assertions.extract_care_denials) as parse:
        p = build_patient_needs_profile({}, story)
    assert parse.call_count == 1
    assert not {'adl_support', 'medication_support'} & {n['parameter_id'] for n in p['needs']}
    for signals in [p['living_strategy']['signals'], p['care_delivery_signals']]:
        assert signals['adl_support_needed'] is False
        assert signals['medication_support_needed'] is False
    assert not {'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE'} & musts(p)


def test_couple_denial_cannot_reappear_as_secure_memory_must():
    p = build_patient_needs_profile({}, 'My parents want to move together. Neither has dementia. They need help with bathing.')
    assert p['living_strategy']['household']['type'] == 'COUPLE'
    assert p['living_strategy']['signals']['memory_care_needed'] is False
    assert 'SECURE_MEMORY_CARE_CONFIRMED' not in musts(p)
    assert {'COUPLE_CORESIDENCE', 'ADL_SUPPORT_AVAILABLE'} <= musts(p)


@pytest.mark.parametrize('story', [
    'He needs help with bathing, dressing and medication. He has dementia.',
    'He does not have dementia, but his wife has dementia. They need help with bathing and medication.',
])
def test_positive_needs_are_preserved_including_other_partner(story):
    p = build_patient_needs_profile({}, story)
    assert {'adl_support', 'medication_support', 'memory_care'} <= {n['parameter_id'] for n in p['needs']}
    assert p['care_delivery_signals']['adl_support_needed'] is True
    assert p['care_delivery_signals']['medication_support_needed'] is True
    assert {'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE', 'SECURE_MEMORY_CARE_CONFIRMED'} <= musts(p)

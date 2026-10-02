"""Care denials and positive care needs are one fact shared by every care layer.

Single authority (owner, 2026-10-01): free text reaches these layers only through the
interpreter's questionnaire_patch (AI_EXTRACTED Structured Profile fields; a denial is a
NEGATED statement whose patch value states the absence). Every care layer -- needs, living
strategy, care-delivery signals and client-intent MUSTs -- then reads that one profile.
Negation parsing of raw text (extract_care_denials) is no longer a decision input; whether
the live model produces the right patch is the Live Golden Interpreter set's job.
"""
from unittest.mock import patch

import pytest

from app.services import care_input_assertions as assertions
from app.services.patient_decision_engine_runtime import build_patient_needs_profile

try:
    from .interpreter_road import decision_facts, interpreter_packet, interpreter_returning, statement
except ImportError:  # pragma: no cover - direct module import
    from interpreter_road import decision_facts, interpreter_packet, interpreter_returning, statement


@pytest.fixture(autouse=True)
def deterministic_intake(monkeypatch):
    monkeypatch.setenv('OPTIME_SEMANTIC_AI_ENABLED', '0')
    monkeypatch.setenv('OPTIME_SEMANTIC_AI_REQUIRED', '0')


def musts(profile):
    return {item['key'] for item in profile['client_intent']['must_haves']}


def _interpreted(story, questionnaire_patch, statements):
    with interpreter_returning(interpreter_packet(questionnaire_patch, statements)):
        return build_patient_needs_profile({}, story)


def _assert_text_alone_changes_nothing(story):
    # AI off (autouse fixture): the story is UNPROCESSED and changes no decision fact.
    assert decision_facts(build_patient_needs_profile({}, story)) == decision_facts(build_patient_needs_profile({}, ''))


INDEPENDENT_STORY = 'She is fully independent and does not need medication support or help with bathing or dressing.'


def test_one_explicit_denial_is_shared_by_every_care_layer():
    with patch.object(assertions, 'extract_care_denials', wraps=assertions.extract_care_denials) as parse:
        p = _interpreted(
            INDEPENDENT_STORY,
            {'assistanceLevel': 'Fully independent'},
            [
                statement('She is fully independent', ['assistanceLevel']),
                statement('does not need medication support or help with bathing or dressing', ['assistanceLevel'], knowledge_state='NEGATED'),
            ],
        )
    # Was parse.call_count == 1: the denial is no longer parsed out of raw text by any layer
    # (owner rule 2026-10-01); a denial parser that still runs sees only empty text.
    assert all(str((call.args or [call.kwargs.get('text', '')])[0] or '') == '' for call in parse.call_args_list), parse.call_args_list
    assert p['canonical_structured_profile']['fields']['assistanceLevel']['provenance'] == 'AI_EXTRACTED'
    assert not {'adl_support', 'medication_support'} & {n['parameter_id'] for n in p['needs']}
    for signals in [p['living_strategy']['signals'], p['care_delivery_signals']]:
        assert signals['adl_support_needed'] is False
        assert signals['medication_support_needed'] is False
    assert not {'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE'} & musts(p)


def test_denial_text_without_the_interpreter_changes_no_decision_fact():
    _assert_text_alone_changes_nothing(INDEPENDENT_STORY)


COUPLE_STORY = 'My parents want to move together. Neither has dementia. They need help with bathing.'


def test_couple_denial_cannot_reappear_as_secure_memory_must():
    p = _interpreted(
        COUPLE_STORY,
        {'relationship': 'Couple', 'memoryStatus': 'No', 'assistanceLevel': 'Help with bathing',
         'humanIntelligenceV2': {'familyProfile': {'coupleStayTogetherPreference': 'Want to move together'}}},
        [
            statement('My parents want to move together.', ['relationship', 'humanIntelligenceV2.familyProfile.coupleStayTogetherPreference']),
            statement('Neither has dementia.', ['memoryStatus'], knowledge_state='NEGATED'),
            statement('They need help with bathing.', ['assistanceLevel']),
        ],
    )
    assert p['living_strategy']['household']['type'] == 'COUPLE'
    assert p['living_strategy']['signals']['memory_care_needed'] is False
    assert 'SECURE_MEMORY_CARE_CONFIRMED' not in musts(p)
    assert {'COUPLE_CORESIDENCE', 'ADL_SUPPORT_AVAILABLE'} <= musts(p)


def test_couple_text_without_the_interpreter_changes_no_decision_fact():
    _assert_text_alone_changes_nothing(COUPLE_STORY)


POSITIVE_CASES = [
    (
        'He needs help with bathing, dressing and medication. He has dementia.',
        {'assistanceLevel': 'Help with bathing, Help with dressing, Help with medications', 'memoryStatus': 'Significant memory issues'},
    ),
    (
        # The interpreter preserves which partner needs which help (coupleAssistance); the
        # couple's shared needs are the union, so the wife's dementia is a household fact.
        'He does not have dementia, but his wife has dementia. They need help with bathing and medication.',
        {'relationship': 'Couple', 'assistanceLevel': 'Help with bathing, Help with medications', 'memoryStatus': 'Significant memory issues',
         'coupleAssistance': 'Husband: no dementia; help with bathing and medication. Wife: dementia; help with bathing and medication.'},
    ),
]


# KNOWN APP GAPS (left failing, no backend/app change allowed here): living_strategy_runtime
# sets medication_support_needed only from free text (the structured "Help with medications"
# never creates MEDICATION_SUPPORT_AVAILABLE), and memory_care_needed only from free text or a
# memoryStatus of yes/dementia/memory care/alzheimer -- never from the intake's and the
# interpreter's own enum value "Significant memory issues" -- so SECURE_MEMORY_CARE_CONFIRMED
# is unreachable from the Structured Profile.
@pytest.mark.parametrize('story,questionnaire_patch', POSITIVE_CASES, ids=[case[0] for case in POSITIVE_CASES])
def test_positive_needs_are_preserved_including_other_partner(story, questionnaire_patch):
    p = _interpreted(story, questionnaire_patch, [statement(story, list(questionnaire_patch))])
    assert {'adl_support', 'medication_support', 'memory_care'} <= {n['parameter_id'] for n in p['needs']}
    assert p['care_delivery_signals']['adl_support_needed'] is True
    assert p['care_delivery_signals']['medication_support_needed'] is True
    assert {'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE', 'SECURE_MEMORY_CARE_CONFIRMED'} <= musts(p)


@pytest.mark.parametrize('story', [case[0] for case in POSITIVE_CASES])
def test_positive_need_text_without_the_interpreter_changes_no_decision_fact(story):
    _assert_text_alone_changes_nothing(story)


def test_client_intent_consumes_the_same_prepared_care_delivery_fact():
    from app.services.client_intent_runtime import build_client_intent
    supplied = {'in_house_only_requested': False}
    with patch('app.services.combined_care_solution_runtime._query_signals', side_effect=AssertionError('Reinterpreted prepared facts')):
        intent = build_client_intent({}, 'Only in-house care', {}, {}, care_delivery_signals=supplied)
    assert intent['in_house_only_requested'] is False

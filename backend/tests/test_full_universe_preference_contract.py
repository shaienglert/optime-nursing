from copy import deepcopy
from unittest.mock import patch

from app.services.decision_pipeline import _apply_combined_care_layer
from app.services.must_ai_nice_pipeline import apply_must_ai_nice_pipeline
from app.services.semantic_preference_runtime import build_dynamic_preference_model
from app.services.canonical_decision_state import derive_canonical_decision_state, DecisionPhase
from test_canonical_decision_state import base_result
from test_must_ai_nice_pipeline import _row


def test_late_in_budget_candidate_survives_care_stage_and_wins_final_comparison():
    rows = [_row(f'Expansion-{i:03}', 'PASS', ['SOCIAL']) for i in range(199)]
    for row in rows:
        row['starting_monthly_price'] = 5250
    winner = _row('Late-in-budget', 'PASS')
    winner['starting_monthly_price'] = 5000
    rows.append(winner)
    for row in rows:
        row['client_intent_fit']['must_pass'] = ['LAS_VEGAS']
    result = {'results': rows, 'decision_intelligence': {'client_intent': {}, 'human_intelligence': {}}}
    with patch('app.services.decision_pipeline._attach_room_pricing_truth'), patch('app.services.combined_care_solution_runtime.attach_combined_care_solutions', return_value={}):
        result = _apply_combined_care_layer(result, {'budget': 5000}, '', 60)
    assert result['results'].index(winner) > 100
    result = apply_must_ai_nice_pipeline(result, {'budget': 5000}, '', 10)
    assert result['results'][0]['canonical_facility_id'] == 'Late-in-budget'
    assert result['decision_intelligence']['ranking_universe_audit']['eligible_candidate_count'] == 200
    assert len(result['results']) == 10


def test_absence_controls_context_and_irrelevant_traces_do_not_become_obligations():
    values = [('No', 'No parking needed', 'parkingRequirement'),
              ('No preference', 'No size preference', 'humanIntelligenceV2.personalityProfile.communitySizePreference'),
              ('Preference', 'Activity importance is preference', 'humanIntelligenceV2.socialProfile.activityRequirementLevel'),
              ('Cautious but open', 'Cautious about moving', 'humanIntelligenceV2.transitionRiskProfile.attitudeTowardMove')]
    statements = [{'raw_text': raw, 'meaning': meaning, 'mapped_parameters': [path], 'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED'} for raw, meaning, path in values]
    statements.append({'raw_text': 'Internal context', 'meaning': 'Internal context', 'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'NOT_DECISION_RELEVANT'})
    packet = {'semantic_ai': {'result': {'preferences': [s['meaning'] for s in statements] + ['A smoke-free environment', 'A lunar astronomy discussion club'], 'statements': statements}}}
    original = deepcopy(packet)
    model = build_dynamic_preference_model(packet)
    assert {p['semantic_meaning'] for p in model['preferences']} == {'A smoke-free environment', 'A lunar astronomy discussion club'}
    assert packet == original  # The complete client statement audit remains available.


def test_empty_dynamic_model_does_not_hide_unresolved_structured_preferences():
    result = base_result()
    result.update(must_eligible_count=5, must_pending_verification_count=0)
    pipeline = {'ai_ranking': {'status': 'DETERMINISTIC_THIN_EVIDENCE_WATERFALL'}, 'dynamic_preferences': {'preference_count': 0}, 'selected_structured_preferences': {'unresolved_candidate_count': 2}}
    result['decision_intelligence']['facility_selection_pipeline'] = pipeline
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.PROVISIONAL_RECOMMENDATION
    assert state.can_show_recommendations
    pipeline['selected_structured_preferences']['unresolved_candidate_count'] = 0
    assert derive_canonical_decision_state(result).phase is DecisionPhase.FINAL_RECOMMENDATION


def test_persistence_stays_bounded_without_truncating_candidate_comparison():
    from app.services.decision_governance_runtime import attach_governed_knowledge_learning_and_audit
    rows = [{'canonical_facility_id': str(i)} for i in range(500)]
    core = {'results': rows, 'recommendation_audit_trace': {'recommendations': rows}}
    with patch('app.services.decision_governance_runtime.load_governed_decision_context', return_value={}), patch('app.services.decision_governance_runtime.persist_recommendation_verification_audits', return_value={}) as persist:
        out = attach_governed_knowledge_learning_and_audit(core=core, questionnaire_state={}, audit_limit=60)
    assert len(persist.call_args.kwargs['core']['results']) == 60
    assert len(persist.call_args.kwargs['core']['recommendation_audit_trace']['recommendations']) == 60
    assert out['results'] is rows and len(rows) == 500


def test_negative_facility_property_is_not_confused_with_absence_of_preference():
    statement = {'raw_text': 'No', 'meaning': 'No smoking is permitted in the community', 'mapped_parameters': ['smokingAllowed'], 'importance': 'NICE', 'knowledge_state': 'KNOWN', 'status': 'USED'}
    model = build_dynamic_preference_model({'semantic_ai': {'result': {'statements': [statement]}}})
    assert model['preference_count'] == 1
    assert model['preferences'][0]['semantic_meaning'] == statement['meaning']


def test_complete_pool_room_prices_use_one_query_and_preserve_total_truth():
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from app.services.decision_pipeline import _attach_room_pricing_truth
    rows = [{'canonical_facility_id': str(i)} for i in range(500)]
    db = MagicMock()
    room = SimpleNamespace(canonical_facility_id='499', room_type_name='Studio', monthly_price_cents=400000, care_fee_cents=50000, mandatory_monthly_fees_cents=10000, pricing_qualifier='EXACT', availability_status='UNKNOWN')
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [room]
    with patch('app.database.SessionLocal', return_value=db):
        _attach_room_pricing_truth(rows)
    assert db.query.call_count == 1
    assert rows[-1]['starting_monthly_price'] == 4600
    assert rows[-1]['total_affordability_status'] == 'KNOWN'
    assert rows[-1]['room_pricing_options'][0]['final_availability_status'] == 'REQUIRES_DIRECT_VERIFICATION'
    db.close.assert_called_once()


def test_prepared_runtime_returns_all_survivors_but_keeps_research_budget():
    from app.services import patient_decision_engine_runtime as runtime
    rows = [_row(str(i), 'PASS') for i in range(200)]
    profile = {'needs': [], 'living_strategy': {}, 'client_intent': {}, 'decision_intelligence': {'human_intelligence': {'decision_readiness': 'READY'}}}
    with patch.object(runtime._governed, 'run_patient_decision_engine', return_value={'patient_needs_profile': profile, 'results': rows}), \
         patch.object(runtime, 'attach_provider_housing_evidence'), \
         patch.object(runtime, 'attach_human_person_fit'), \
         patch.object(runtime, 'attach_client_intent_fit'), \
         patch.object(runtime, 'attach_nearby_place_fit'), \
         patch.object(runtime, '_is_rankable_candidate', return_value=True), \
         patch.object(runtime, 'attach_agent_evidence_and_queue_gaps', return_value={}) as research, \
         patch.object(runtime, '_care_partner_layer', return_value={}), \
         patch.object(runtime, 'attach_governed_knowledge_learning_and_audit', side_effect=lambda **kw: kw['core']) as audit:
        result = runtime._run_prepared_decision({}, '', 60, prepared_profile=profile, return_full_universe=True)
    assert len(result['results']) == 200
    assert len(research.call_args.args[0]) <= 60
    assert audit.call_args.kwargs['audit_limit'] == 60

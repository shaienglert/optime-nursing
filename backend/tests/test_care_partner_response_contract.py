from copy import deepcopy
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from app import main


@pytest.mark.parametrize('options', [[], [{
    'agency_id': 'NV-PCA-TEST', 'agency_name': 'Synthetic Contract Test Agency',
    'hourly_rate': 'UNKNOWN', 'availability_status': 'VERIFY_WITH_PROVIDER',
    'source': 'contract fixture',
}]])
def test_care_partner_options_survive_http_and_stored_decision(monkeypatch, options):
    engine_result = {
        'patient_needs_profile': {}, 'results': [], 'result_count': 0,
        'total_candidates_scored': 0, 'availability_policy': 'VERIFY_WITH_FACILITY',
        'care_partner_options': deepcopy(options),
    }
    monkeypatch.setattr(main, 'run_patient_decision_engine', lambda **kwargs: engine_result)
    remember = Mock(return_value='stored-contract-test')
    monkeypatch.setattr(main, 'remember_decision_result', remember)
    database = Mock()
    database.query.return_value.filter.return_value.all.return_value = []
    previous = main.app.dependency_overrides.copy()
    main.app.dependency_overrides[main.get_db] = lambda: database
    try:
        response = TestClient(main.app).post('/decision-engine/recommendations', json={
            'questionnaire_state': {}, 'natural_language_query': '',
        })
        assert response.status_code == 200
        assert response.json()['care_partner_options'] == options
        assert response.json()['decision_id'] == 'stored-contract-test'
        assert remember.call_args.args[0]['care_partner_options'] == options
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous)


def test_absent_care_partner_options_default_to_empty():
    served = main.PatientDecisionEngineOut.model_validate({
        'patient_needs_profile': {}, 'results': [], 'result_count': 0,
        'total_candidates_scored': 0, 'availability_policy': 'VERIFY_WITH_FACILITY',
    }).model_dump()
    assert served['care_partner_options'] == []

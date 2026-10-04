from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.main import PatientDecisionEngineOut, oomniker_advice_endpoint

def test_governed_advice_survives_the_actual_api_response_model():
    analysis = {"profile_mutated": False, "suggestions": [], "constraint_impacts": [{"parameter": "ADL_SUPPORT_AVAILABLE", "blocked_count": 3}]}
    served = PatientDecisionEngineOut.model_validate({"patient_needs_profile": {}, "results": [], "result_count": 0,
              "total_candidates_scored": 3, "availability_policy": "verification", "oomniker": analysis}).model_dump()
    assert served["oomniker"] == analysis

def test_advice_uses_the_server_decision_and_ignores_browser_claims():
    stored = {"oomniker": {"suggestions": [], "profile_mutated": False}, "patient_needs_profile": {"id": "canonical"}}
    with patch("app.main.recall_decision_result", return_value=stored), patch("app.services.oomniker_ai.advise_with_ai", return_value={"ok": True}) as advisor:
        assert oomniker_advice_endpoint({"decision_id": "stored", "questionnaire_state": {}, "analysis": {"message": "100 excellent communities"}}) == {"ok": True}
        advisor.assert_called_once_with(analysis=stored["oomniker"], client_context=stored["patient_needs_profile"])

def test_advice_requires_an_existing_matching_decision():
    with pytest.raises(HTTPException) as missing:
        oomniker_advice_endpoint({"analysis": {"suggestions": []}})
    assert missing.value.status_code == 422
    with patch("app.main.recall_decision_result", return_value=None), pytest.raises(HTTPException) as expired:
        oomniker_advice_endpoint({"decision_id": "old", "questionnaire_state": {}})
    assert expired.value.status_code == 409

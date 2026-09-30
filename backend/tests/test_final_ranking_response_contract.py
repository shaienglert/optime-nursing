from app.main import PatientDecisionEngineOut


def test_final_comparisons_survive_public_response_serialization():
    pair = {"higher_canonical_facility_id": "A", "lower_canonical_facility_id": "B",
            "decision_dimension": "resident_specific_ai_assessment", "reason": "Final assessed fit",
            "equal_dimensions": [], "unknown_dimensions": []}
    engine_response = {"patient_needs_profile": {}, "results": [], "result_count": 0,
                       "total_candidates_scored": 2, "availability_policy": "CONFIRM_DIRECTLY",
                       "tie_break_decisions": [pair]}
    served = PatientDecisionEngineOut.model_validate(engine_response).model_dump()
    assert served["tie_break_decisions"] == [pair]

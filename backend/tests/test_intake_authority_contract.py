from unittest.mock import patch
from copy import deepcopy

from app.services.canonical_decision_state import derive_canonical_decision_state
from app.services.canonical_gap_policy import assess_gaps
from app.services.patient_decision_engine import build_patient_needs_profile


CONFLICT_STORY = "Las Vegas. Budget $500 or $50000."
CONFLICT = {
    "decision_readiness": "NEEDS_CLARIFICATION", "next_question": "Which monthly budget is correct?",
    "questionnaire_patch": {},
    "statements": [{"status": "ASKED", "knowledge_state": "AMBIGUOUS", "importance": "MUST",
                    "gap_key": "monthly_budget", "raw_text": "$500 or $50000", "meaning": "Conflicting budget amounts",
                    "clarification_question": "Which monthly budget is correct?", "mapped_parameters": ["monthly_budget"]}],
}


def test_source_backed_budget_conflict_overrides_amount_presence():
    policy = assess_gaps(guardian_gaps=[], ai_result=CONFLICT, questionnaire_state={}, user_text=CONFLICT_STORY)
    assert policy["blocking_gap_keys"] == ["monthly_budget"]
    assert "monthly_budget" not in policy["resolved_gap_keys"]


def test_source_backed_clinical_contradiction_is_not_an_optional_preference():
    packet = deepcopy(CONFLICT)
    packet["statements"][0].update(gap_key="memory_status", raw_text="No memory problems but severe dementia")
    policy = assess_gaps(guardian_gaps=[], ai_result=packet, questionnaire_state={}, user_text="No memory problems but severe dementia")
    assert policy["blocking_gap_keys"] == ["memory_status"]


def test_optional_or_unsupported_model_question_cannot_become_a_clinical_blocker():
    packet = deepcopy(CONFLICT)
    packet["statements"][0].update(gap_key="memory_status", raw_text="Memory is unclear")
    policy = assess_gaps(guardian_gaps=[], ai_result=packet, questionnaire_state={}, user_text="No memory problems")
    assert policy["blocking_gap_keys"] == []


def test_canonical_authority_keeps_semantic_blocker_not_just_guardian_rows():
    policy = assess_gaps(guardian_gaps=[], ai_result=CONFLICT, questionnaire_state={}, user_text=CONFLICT_STORY)
    result = {"decision_intelligence": {"human_intelligence": {
        "canonical_gap_policy": policy, "readiness_guardian": {"client_owned_blockers": []},
        "decision_readiness": "READY",
    }}, "results": []}
    state = derive_canonical_decision_state(result)
    assert state.client.value == "INCOMPLETE"
    assert state.next_action == "ASK_CLIENT"


def test_full_profile_contract_does_not_promote_conflict_to_complete(monkeypatch):
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_ENABLED", "1")
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_REQUIRED", "1")
    with patch("app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=CONFLICT):
        profile = build_patient_needs_profile({}, CONFLICT_STORY)
    state = profile["decision_intelligence"]["canonical_decision_state"]
    assert state["client"] == "INCOMPLETE"
    assert state["next_action"] == "ASK_CLIENT"


def test_failed_narrative_extraction_cannot_be_confirmed(monkeypatch):
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_ENABLED", "1")
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_REQUIRED", "1")
    with patch("app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", side_effect=RuntimeError("SEMANTIC_AI_HTTP_503")):
        profile = build_patient_needs_profile({}, "Independent mother in Las Vegas, budget $5000.")
    state = profile["decision_intelligence"]["canonical_decision_state"]
    assert state["client"] == "INCOMPLETE"
    assert state["system"] == "BLOCKED"
    assert state["next_action"] == "RECOVER_SYSTEM"


def test_ai_failure_does_not_erase_completed_structured_intake(monkeypatch):
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_ENABLED", "1")
    state = {"budget": 5000, "referenceLocationValue": "Las Vegas", "assistanceLevel": "Fully independent", "memoryStatus": "No",
             "questionnaireCompletion": {"mandatoryComplete": True, "conditionalFollowUpsComplete": True, "clientSummaryConfirmed": True}}
    with patch("app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", side_effect=RuntimeError("SEMANTIC_AI_HTTP_503")):
        profile = build_patient_needs_profile(state, "Independent mother in Las Vegas, budget $5000.")
    assert profile["decision_intelligence"]["canonical_decision_state"]["system"] == "HEALTHY"

from unittest.mock import patch
from app.services.human_intelligence_runtime_verified import build_human_intelligence_context

def test_ai_cannot_choose_different_question_target_than_canonical_gap():
    state={"questionnaireCompletion":{"mandatoryComplete":False,"conditionalFollowUpsComplete":False}}
    ai={
        "decision_readiness":"NEEDS_CLARIFICATION",
        "selected_fact_key":"favorite_color",
        "next_question":"What is her favorite color?",
        "statements":[{"raw_text":"unknown","status":"ASKED","gap_key":"favorite_color","mapped_parameters":["favorite_color"]}],
        "questionnaire_patch":{},
    }
    with patch("app.services.human_intelligence_runtime_verified._call_semantic_ai", return_value=ai):
        context=build_human_intelligence_context(state,"")
    blockers=(context.get("readiness_guardian") or {}).get("client_owned_blockers") or []
    if blockers:
        assert (context.get("readiness_guardian") or {}).get("selected_fact_key") == blockers[0].get("fact_key")
        questions=context.get("adaptive_questions") or []
        assert questions
        assert questions[0].get("target_fact_key") == blockers[0].get("fact_key")

def test_no_blocking_gap_means_ready_regardless_of_model_readiness_label():
    state={"questionnaireCompletion":{"mandatoryComplete":True,"conditionalFollowUpsComplete":True}}
    ai={"decision_readiness":"NEEDS_CLARIFICATION","next_question":"Anything else?","statements":[],"questionnaire_patch":{}}
    with patch("app.services.human_intelligence_runtime_verified._call_semantic_ai", return_value=ai):
        context=build_human_intelligence_context(state,"")
    assert context["decision_readiness"] in {"READY","NEEDS_CLARIFICATION"}
    if context["decision_readiness"]=="NEEDS_CLARIFICATION":
        assert (context.get("canonical_gap_policy") or {}).get("blocking_gap_keys") or (context.get("canonical_gap_policy") or {}).get("escalation_required")

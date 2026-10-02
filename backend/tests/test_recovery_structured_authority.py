from app.services.living_strategy_runtime import build_living_strategy_context

def test_recovery_strategy_comes_from_structured_episode_not_story_text():
    state={"humanIntelligenceV2":{"transitionRiskProfile":{"recentProcedure":"Yes","procedureType":"spinal fusion","expectedRecovery":"Yes","temporarySupportMonths":"3","postHospitalRehabNeed":"Yes"}}}
    out=build_living_strategy_context(state,"")
    s=out["signals"]
    assert s["post_surgical"] is True
    assert s["spine_or_back_surgery"] is True
    assert s["rehabilitation_need_detected"] is True
    assert s["expected_recovery"] is True
    assert s["temporary_support_duration_months"]==3.0

def test_story_text_cannot_create_recovery_episode_without_structured_fields():
    out=build_living_strategy_context({},"spinal surgery, expected to recover in 3 months")
    s=out["signals"]
    assert s["post_surgical"] is False
    assert s["expected_recovery"] is False
    assert s["temporary_support_duration_months"]=="UNKNOWN"

from copy import deepcopy
from unittest.mock import Mock, patch

from app.services import decision_pipeline
from app.services import patient_decision_engine_runtime as runtime
from app.services.canonical_decision_state import apply_canonical_decision_state_authority


def test_pipeline_passes_one_prepared_profile_to_matching():
    """A second interpreter must not replace the intake accepted by the gate."""
    profile = {"needs": [], "decision_intelligence": {"human_intelligence": {
        "decision_readiness": "READY", "readiness_guardian": {"client_owned_blockers": []},
    }}}
    apply_canonical_decision_state_authority(profile)
    builder = Mock(return_value=profile)
    runner = Mock(return_value={"patient_needs_profile": deepcopy(profile), "decision_intelligence": deepcopy(profile["decision_intelligence"]), "results": []})
    identity = lambda result, *args, **kwargs: result
    with patch.object(decision_pipeline, "_apply_combined_care_layer", side_effect=identity), \
         patch("app.services.semantic_facility_requirements.apply_semantic_facility_requirements", side_effect=identity), \
         patch("app.services.must_ai_nice_pipeline.apply_must_ai_nice_pipeline", side_effect=identity), \
         patch("app.services.ai_process_owner_guard_patch.attach_ai_process_owner_guarded", side_effect=identity), \
         patch.object(decision_pipeline, "_attach_pipeline_trace", side_effect=identity):
        decision_pipeline.run_decision_pipeline({"budget": 5000}, "Las Vegas", 10, profile_builder=builder, runner=runner)
    builder.assert_called_once()
    runner.assert_called_once()
    assert runner.call_args.kwargs["prepared_profile"] is profile


def test_matching_does_not_reinterpret_prepared_client_context():
    profile = {"needs": [], "living_strategy": {}, "client_intent": {}, "decision_intelligence": {"human_intelligence": {"decision_readiness": "READY"}}}
    with patch.object(runtime._governed, "run_patient_decision_engine", return_value={"patient_needs_profile": profile, "results": []}), \
         patch.object(runtime, "build_human_intelligence_context", side_effect=AssertionError("second semantic interpretation")), \
         patch.object(runtime, "build_client_intent", side_effect=AssertionError("second client-intent construction")), \
         patch.object(runtime, "build_living_strategy_context", side_effect=AssertionError("second strategy interpretation")), \
         patch.object(runtime, "attach_provider_housing_evidence"), \
         patch.object(runtime, "attach_human_person_fit"), \
         patch.object(runtime, "attach_client_intent_fit"), \
         patch.object(runtime, "attach_agent_evidence_and_queue_gaps", return_value={}), \
         patch.object(runtime, "_care_partner_layer", return_value={}), \
         patch.object(runtime, "attach_governed_knowledge_learning_and_audit", side_effect=lambda **kw: kw["core"]):
        result = runtime._run_prepared_decision({}, "", 10, prepared_profile=profile)
    assert result["decision_intelligence"]["human_intelligence"] is profile["decision_intelligence"]["human_intelligence"]


def test_importing_services_does_not_register_import_interceptors():
    import sys
    assert not any(type(finder).__name__ == "_GovernedDecisionEngineFinder" for finder in sys.meta_path)

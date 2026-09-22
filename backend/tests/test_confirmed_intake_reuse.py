from copy import deepcopy
from unittest.mock import Mock, patch

import pytest

from app.services import decision_result_store as store
from app.services import combined_care_solution_runtime as combined
from app.services import decision_pipeline as pipeline


@pytest.fixture(autouse=True)
def artifact_database(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.decision_artifact import DecisionArtifact
    engine = create_engine(f"sqlite:///{tmp_path / 'artifacts.db'}")
    DecisionArtifact.__table__.create(engine)
    monkeypatch.setattr(store, "SessionLocal", sessionmaker(bind=engine))
    yield
    engine.dispose()


def profile():
    return {"needs": [], "decision_intelligence": {"canonical_decision_state": {
        "authoritative": True, "client": "COMPLETE", "system": "READY",
    }}}


def test_snapshot_bound_to_case_but_not_confirmation_acknowledgement():
    state = {"budget": 5000, "notes": "mother"}
    p = profile()
    token = store.remember_intake_profile(p, questionnaire_state=state, natural_language_query="mother")
    p["needs"].append({"forged": True})
    confirmed = {**state, "questionnaireCompletion": {"clientSummaryConfirmed": True}, "aiProcessContinuity": {"phase": "RECOMMEND", "lastEvent": "RESULTS_VIEWED", "updatedAt": "now"}}
    result = store.recall_intake_profile(token, questionnaire_state=confirmed, natural_language_query="mother")
    assert result["profile"]["needs"] == []
    result["profile"]["needs"].append({"changed": True})
    assert store.recall_intake_profile(token, questionnaire_state=state, natural_language_query="mother")["profile"]["needs"] == []
    assert store.recall_intake_profile(token, questionnaire_state={**state, "budget": 9000}, natural_language_query="mother") is None
    assert store.recall_intake_profile(token, questionnaire_state=state, natural_language_query="father") is None
    assert store.recall_intake_profile("forged", questionnaire_state=state, natural_language_query="mother") is None
    with patch.object(store.time, "time", return_value=store.time.time() + store._TTL_SECONDS + 1):
        assert store.recall_intake_profile(token, questionnaire_state=state, natural_language_query="mother") is None


def test_incomplete_or_blocked_profile_cannot_be_frozen():
    for field, value in [("client", "INCOMPLETE"), ("system", "BLOCKED")]:
        p = profile()
        p["decision_intelligence"]["canonical_decision_state"][field] = value
        with pytest.raises(ValueError):
            store.remember_intake_profile(p, questionnaire_state={}, natural_language_query="")


def test_prepared_pipeline_never_calls_profile_builder():
    p = profile()
    builder = Mock(side_effect=AssertionError("Reinterpreted confirmed profile"))
    runner = Mock(return_value=None)
    pipeline.run_decision_pipeline({}, "", 5, profile_builder=builder, runner=runner, prepared_profile=p)
    builder.assert_not_called()
    assert runner.call_args.kwargs["prepared_profile"] is p


def test_combined_care_consumes_prepared_signals_for_every_facility():
    signals = combined._query_signals({}, "Needs bathing help temporarily")
    rows = [{"canonical_facility_id": "test-a"}, {"canonical_facility_id": "test-b"}]
    expected = [combined.build_combined_care_solution(deepcopy(row), {}, "Needs bathing help temporarily") for row in rows]
    with patch.object(combined, "_query_signals", side_effect=AssertionError("Reinterpreted case downstream")):
        summary = combined.attach_combined_care_solutions(rows, {}, "different narrative", prepared_signals=signals)
    assert summary["signals"] is signals
    assert [r["combined_care_solution"] for r in rows] == expected


def test_recommendation_endpoint_uses_server_artifact_and_rejects_stale_inputs():
    from app import main
    from unittest.mock import MagicMock
    state = {"budget": 5000}
    p = profile()
    token = store.remember_intake_profile(p, questionnaire_state=state, natural_language_query="mother")
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    result = {"patient_needs_profile": p, "results": [], "result_count": 0,
              "total_candidates_scored": 0, "availability_policy": "test"}
    with patch.object(main, "run_patient_decision_engine", return_value=result) as engine:
        main.post_patient_decision_recommendations(main.PatientDecisionEngineRequestIn(
            questionnaire_state={**state, "questionnaireCompletion": {"clientSummaryConfirmed": True}},
            natural_language_query="mother", intake_profile_id=token), db)
        assert engine.call_args.kwargs["prepared_profile"] == p
        assert engine.call_args.kwargs["questionnaire_state"] == state
        engine.reset_mock()
        with pytest.raises(main.HTTPException) as exc:
            main.post_patient_decision_recommendations(main.PatientDecisionEngineRequestIn(
                questionnaire_state={"budget": 8000}, natural_language_query="mother", intake_profile_id=token), db)
        assert exc.value.status_code == 409
        engine.assert_not_called()


def test_profile_endpoint_exposes_only_server_generated_handle():
    from app import main
    p = {**profile(), "generated_from": {}, "need_tags": [], "priority_parameter_ids": [], "natural_language_mapping": {}}
    with patch.object(main, "build_patient_needs_profile", return_value=p):
        result = main.post_patient_needs_profile(main.PatientNeedsProfileRequestIn(questionnaire_state={}, natural_language_query=""))
    response = main.PatientNeedsProfileOut.model_validate(result).model_dump()
    assert response["intake_profile_id"]
    artifact = store.recall_intake_profile(response["intake_profile_id"], questionnaire_state={}, natural_language_query="")
    assert artifact["profile"]["needs"] == []


def test_care_partner_consumes_prepared_requirements_without_reading_story():
    from app.services import patient_decision_engine_runtime as runtime
    requirements = {"test_requirement": True}
    with patch.object(runtime, "_prepare_care_partner_requirements", side_effect=AssertionError("Reinterpreted case")), \
         patch.object(runtime, "build_verified_care_partner_context", return_value={}) as lookup:
        runtime._care_partner_layer({}, {}, "different story", prepared_profile={"care_partner_requirements": requirements})
    lookup.assert_called_once_with(requirements, limit=10)

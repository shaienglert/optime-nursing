from copy import deepcopy
import sys
from types import ModuleType

import pytest

from app.services.questionnaire_answer_accounting import (
    attach_questionnaire_answer_accounting, build_questionnaire_answer_accounting,
)


def packet(canonical=None, statements=None, needs=None, strict=True):
    return {"patient_needs_profile": {"canonical_decision_questionnaire": canonical or {}, "needs": needs or []},
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "wire_contract": {"schema_constrained": strict}, "statements": statements or []}}}}}


def trace(path, quote, role="NICE", status="USED"):
    return {"mapped_parameters": [path], "raw_text": quote, "importance": role,
            "status": status, "knowledge_state": "KNOWN"}


def test_arbitrary_new_question_is_not_hidden_by_a_fixed_catalog():
    audit = build_questionnaire_answer_accounting({"newProperty": "Pottery kiln"}, packet())
    assert audit["unaccounted_count"] == 1
    assert audit["answers"][0]["answer"] == "Pottery kiln"


def test_preserving_answer_is_not_claimed_as_decision_use():
    state = {"medicalCareProfile": {"recentFalls": "More than one"}}
    audit = build_questionnaire_answer_accounting(state, packet(state))
    assert audit["canonical_preserved_count"] == 1
    assert audit["answers"][0]["status"] == "PRESERVED_NOT_TRACED"
    assert audit["untraced_count"] == 1


def test_transfer_need_can_be_linked_without_client_intent_entry():
    state = {"medicalCareProfile": {"transferAssistance": "Two people"}}
    needs = [{"parameter_id": "transfer_assistance", "user_evidence_source": "questionnaire.medicalCareProfile.transferAssistance"}]
    row = build_questionnaire_answer_accounting(state, packet(state, needs=needs))["answers"][0]
    assert row["status"] == "NEED_LINKED"
    assert row["need_parameter_ids"] == ["transfer_assistance"]


def test_source_path_alone_does_not_credit_each_selection():
    state = {"medicalCareProfile": {"needs": ["Wound care", "Other"]}}
    needs = [{"parameter_id": "wound_care", "user_evidence_source": "questionnaire.medicalCareProfile.needs"}]
    rows = build_questionnaire_answer_accounting(state, packet(state, needs=needs))["answers"]
    assert all(row["status"] == "PRESERVED_NOT_TRACED" for row in rows)


def test_each_arbitrary_list_selection_needs_its_own_quote():
    state = {"activities": ["Pottery", "Late concerts"]}
    audit = build_questionnaire_answer_accounting(state, packet(state, [trace("activities", "Pottery")]))
    assert [r["status"] for r in audit["answers"]] == ["SOURCE_TRACED", "PRESERVED_NOT_TRACED"]
    assert [r["selection_index"] for r in audit["answers"]] == [0, 1]


@pytest.mark.parametrize("path,quote", [("wrongPath", "Music"), ("activities", "Musical activities"), ("activities", "music")])
def test_wrong_path_or_paraphrase_cannot_claim_source_trace(path, quote):
    state = {"activities": ["Music"]}
    row = build_questionnaire_answer_accounting(state, packet(state, [trace(path, quote)]))["answers"][0]
    assert row["status"] == "PRESERVED_NOT_TRACED"


def test_advisory_or_legacy_packet_cannot_claim_authoritative_interpretation():
    state = {"activities": ["Music"]}
    result = packet(state, [trace("activities", "Music")], strict=False)
    result["decision_intelligence"]["human_intelligence"]["semantic_ai"]["result"]["preferences"] = ["Music"]
    assert build_questionnaire_answer_accounting(state, result)["answers"][0]["status"] == "PRESERVED_NOT_TRACED"


@pytest.mark.parametrize("answer", [False, 0, "No", "Not important", "No preference"])
def test_explicit_negative_neutral_and_zero_answers_are_retained(answer):
    audit = build_questionnaire_answer_accounting({"answer": answer}, packet({"answer": answer}))
    assert audit["answer_count"] == 1
    assert audit["answers"][0]["answer"] == answer


def test_false_is_not_preserved_by_numeric_zero():
    row = build_questionnaire_answer_accounting({"answer": False}, packet({"answer": 0}))["answers"][0]
    assert row["canonical_preserved"] is False


def test_context_and_uncertainty_are_reported_without_new_preference():
    source = trace("continuum", "Not important", "CONTEXT", "NOT_DECISION_RELEVANT")
    result = packet({"continuum": "Not important"}, [source])
    row = build_questionnaire_answer_accounting({"continuum": "Not important"}, result)["answers"][0]
    assert row["semantic_traces"][0]["role"] == "CONTEXT"
    assert row["need_parameter_ids"] == []
    assert "client_intent" not in result["decision_intelligence"]


def test_nested_destination_and_adaptive_answer_sources_are_preserved():
    state = {"destinations": [{"address": "Synthetic address"}], "adaptiveSignals": {"fact": "Synthetic answer"}}
    audit = build_questionnaire_answer_accounting(state, packet(state))
    assert {r["answer_path"] for r in audit["answers"]} == {"destinations[0].address", "adaptiveSignals.fact"}
    assert audit["canonical_preserved_count"] == 2


def test_empty_values_and_completion_bookkeeping_do_not_inflate_coverage():
    state = {"unused": "", "missing": None, "empty": [], "questionnaireCompletion": {"confirmed": True}}
    audit = build_questionnaire_answer_accounting(state, packet())
    assert audit["answer_count"] == 0
    assert "coverage_percent" not in audit


def test_observation_does_not_mutate_inputs_decision_or_ranking():
    state = {"answer": "Music"}
    result = packet(state)
    result["results"] = [{"rank_position": 1, "eligibility_status": "ELIGIBLE"}]
    original, original_state = deepcopy(result), deepcopy(state)
    audit = build_questionnaire_answer_accounting(state, result)
    assert result == original and state == original_state
    attach_questionnaire_answer_accounting(result, state)
    assert result["results"] == original["results"]
    assert result["decision_intelligence"] == original["decision_intelligence"]
    assert result["recommendation_audit_trace"]["questionnaire_answer_accounting"] == audit


def test_pipeline_completion_boundary_attaches_original_answer_audit(monkeypatch):
    from app.services.decision_pipeline import _attach_pipeline_trace
    module = ModuleType("app.services.decision_pipeline_trace")
    module.attach_decision_pipeline_trace = lambda result: result
    monkeypatch.setitem(sys.modules, "app.services.decision_pipeline_trace", module)
    result = _attach_pipeline_trace(packet(), {"newQuestion": "Original answer"})
    assert result["questionnaire_answer_accounting"]["unaccounted_count"] == 1


def test_transport_strips_private_fields_recursively_after_accounting(monkeypatch):
    from app.services.decision_pipeline import _attach_pipeline_trace
    module = ModuleType("app.services.decision_pipeline_trace")
    module.attach_decision_pipeline_trace = lambda result: result
    monkeypatch.setitem(sys.modules, "app.services.decision_pipeline_trace", module)
    original = {"results": [{"__rank_comparison_trace": {"secret": 1}, "public": {"__hidden": 2, "visible": 3}}],
                "research": [{"__private": 4}]}
    public = _attach_pipeline_trace(original, {})
    assert public["results"] == [{"public": {"visible": 3}}]
    assert public["research"] == [{}]
    assert "__rank_comparison_trace" in original["results"][0]


def test_exact_nearby_answer_is_credited_only_when_final_key_differs():
    from app.services.must_ai_nice_pipeline import _layered_rank
    state = {"nearbyPlaces": ["Shopping", "Library"]}
    result = packet(state)
    candidates = []
    for distance in (1., 2.):
        candidates.append({"nearby_place_fit": {"status": "KNOWN", "importance": "Important",
                                                "fit_band": 2, "average_distance_miles": distance},
                           "__ranking_answer_sources": [{"answer_path": "nearbyPlaces", "selection_index": 0,
                                "answer": "Shopping", "dimensions": ["requested_nearby_distance"]}]})
    result["results"] = _layered_rank(candidates)
    rows = build_questionnaire_answer_accounting(state, result)["answers"]
    assert rows[0]["status"] == "RANKING_EFFECT_TRACED"
    assert rows[1]["status"] == "PRESERVED_NOT_TRACED"
    candidates[1]["nearby_place_fit"]["average_distance_miles"] = 1.
    result["results"] = _layered_rank(candidates)
    assert build_questionnaire_answer_accounting(state, result)["answers"][0]["status"] == "PRESERVED_NOT_TRACED"


def test_deterministic_activity_and_continuity_consumers_link_exact_inputs():
    from app.services.client_intent_runtime import build_client_intent
    state = {"futureCarePreference": "Preferred", "humanIntelligenceV2": {
        "socialProfile": {"hobbyParticipation": ["Pottery", "Library"], "activityRequirementLevel": "Required"},
        "futureCareProfile": {"continuumOfCarePreference": "Somewhat important"}}}
    result = packet(state)
    result["decision_intelligence"]["client_intent"] = build_client_intent(state, "", {}, {})
    rows = build_questionnaire_answer_accounting(state, result)["answers"]
    assert [r["status"] for r in rows[:4]] == ["INTENT_LINKED"] * 4
    assert rows[-1]["status"] == "PRESERVED_NOT_TRACED"
    assert rows[-1]["control_diagnostics"] == ["UNRECOGNIZED_CONTROL_VALUE"]
    assert all(not r["ranking_effect_dimensions"] for r in rows)

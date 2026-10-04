from __future__ import annotations

import os
from unittest.mock import patch

if __package__:
    from .priced_candidate_fixture import priced_payloads
else:
    from priced_candidate_fixture import priced_payloads

import pytest

from app.services.facility_parameter_service import refresh_runtime_cache
from app.services.patient_decision_engine import run_patient_decision_engine


@pytest.fixture(autouse=True)
def verified_budget_and_medication_evidence_for_strategy_goldens():
    # These tests exercise strategy among verified candidates. Price-unknown cases
    # belong in the pending-MUST tests and must not supply a ranked shortlist.
    with patch("app.services.governed_evidence_runtime.agent_and_provider_payloads",
               side_effect=priced_payloads([{"published_rates_verified": True, "medication_support_verified": True}])):
        yield


def _deterministic_rank_for_quality_gate(rows, client_intent, human_context, strategy, deterministic_fallback_key):
    """Golden decision-quality cases test eligibility/strategy, not a network model.

    The candidate-ranking contract has its own mocked tests. Keeping this suite local
    prevents an inherited CI secret/configuration from changing which facilities reach
    the strategy assertions.
    """
    del client_intent, human_context, strategy
    ordered = sorted(rows, key=deterministic_fallback_key)
    return ordered, {"status": "AI_BATCH_RANKED", "candidate_count": len(ordered), "closed_world_validated": True}


def _run_ready(questionnaire: dict, query: str, limit: int = 5) -> dict:
    ai_result = {"decision_readiness": "READY", "next_question": None, "statements": []}
    with patch.dict(
        os.environ,
        {
            "OPTIME_CANONICAL_MARKET": "las-vegas",
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_SEMANTIC_AI_REQUIRED": "1",
        },
        clear=False,
    ), patch(
        "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai",
        return_value=ai_result,
    ), patch(
        "app.services.must_ai_nice_pipeline.rank_must_eligible_candidates",
        side_effect=_deterministic_rank_for_quality_gate,
    ), patch(
        "app.services.ai_process_owner_guard_patch.attach_ai_process_owner_guarded",
        side_effect=lambda result, questionnaire_state, natural_language_query: result,
    ):
        refresh_runtime_cache("golden_topn_case")
        return run_patient_decision_engine(questionnaire, query, limit=limit)


def _modalities(row: dict) -> set[str]:
    values = {str(row.get("canonical_type") or "UNKNOWN").upper()}
    values.update(str(value or "UNKNOWN").upper() for value in row.get("housing_modalities") or [])
    return values


def test_golden_independent_client_top5_is_led_by_independent_products():
    result = _run_ready(
        {
            "relationship": "My mother",
            "ageGroup": "80-84",
            "assistanceLevel": "Fully independent",
            "memoryStatus": "No",
            "budget": 8000,
            "locationCity": "Las Vegas",
        },
        (
            "My mother is 82 and is looking for senior living in Las Vegas. "
            "She is fully independent with bathing, dressing, toileting, transfers and medications. "
            "She has no memory concerns, no mobility limitation, and no medical or nursing needs. "
            "Her monthly budget is $8,000."
        ),
    )
    rows = result.get("results") or []
    assert len(rows) == 5, result
    assert all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in rows)
    independent = [row for row in rows if _modalities(row) & {"INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"}]
    assert len(independent) >= 3, [(row.get("facility_name"), sorted(_modalities(row))) for row in rows]
    assert _modalities(rows[0]) & {"INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"}, rows[0]
    small_rfg = [
        row for row in rows
        if row.get("canonical_type") == "ASSISTED_LIVING_RFG"
        and not (_modalities(row) & {"INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"})
    ]
    assert len(small_rfg) <= 1, [row.get("facility_name") for row in rows]


def test_golden_ongoing_adl_client_top5_is_assisted_living_primary_fit():
    result = _run_ready(
        {
            "relationship": "Dad",
            "ageGroup": "80-84",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "budget": 6500,
            "locationCity": "Las Vegas",
        },
        (
            "My father is 84 and lives in Las Vegas. He needs ongoing daily help with bathing, dressing and medications. "
            "He is mentally alert, has no dementia, remains mobile, and is not expected to recover to full independence. "
            "His monthly budget is $6,500."
        ),
    )
    rows = result.get("results") or []
    assert len(rows) == 5, result
    assert all(row.get("canonical_type") == "ASSISTED_LIVING_RFG" for row in rows), [
        (row.get("facility_name"), row.get("canonical_type")) for row in rows
    ]
    assert all((row.get("care_setting_fit") or {}).get("status") == "PRIMARY_FIT" for row in rows)
    assert all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in rows)


_MEMORY_STORY = (
    "My mother is 82, has diagnosed dementia and needs memory-care supervision and daily assistance. "
    "We need an appropriate memory care setting in Las Vegas. Her monthly budget is $9,000."
)
_MEMORY_CLIENT = {
    "relationship": "My mother",
    "ageGroup": "80-84",
    "assistanceLevel": "Needs supervision and daily assistance",
    # The intake's own enum value; the legacy free label "Dementia" never created the
    # memory-care need in the engine.
    "memoryStatus": "Significant memory issues",
    "budget": 9000,
    "locationCity": "Las Vegas",
}


def _memory_client(wandering=None):
    client = dict(_MEMORY_CLIENT)
    if wandering is not None:
        client["humanIntelligenceV2"] = {"transitionRiskProfile": {"wanderingConcerns": wandering}}
    return client


def _must_keys(result):
    return {item["key"] for item in result["decision_intelligence"]["client_intent"]["must_haves"]}


def test_golden_memory_label_alone_asks_the_safety_question_instead_of_assuming_a_secured_unit():
    # Owner decision: a memory label never creates a secured-unit MUST by itself. With the
    # wandering/security question unanswered the interview asks it and withholds results.
    result = _run_ready(_memory_client(), _MEMORY_STORY)
    state = result["decision_intelligence"]["canonical_decision_state"]
    assert state["next_action"] == "ASK_CLIENT" and state["client"] == "INCOMPLETE"
    assert not {"SECURE_MEMORY_CARE_CONFIRMED", "SECURED_UNIT_AVAILABLE"} & _must_keys(result)
    assert "memory_safety_need" in {q["question_key"] for q in result["decision_intelligence"]["living_strategy"]["guardian_clarification_candidates"]}
    assert result["result_count"] == 0


@pytest.mark.parametrize("answer", ["No", "Not sure"])
def test_golden_memory_client_with_answered_safety_question_gets_results(answer):
    # After the question is answered (even "Not sure") the client progresses and receives
    # results: no secured-unit MUST and only communities with confirmed memory care.
    result = _run_ready(_memory_client(answer), _MEMORY_STORY)
    rows = result.get("results") or []
    assert rows, result["decision_intelligence"]["canonical_decision_state"]
    assert not {"SECURE_MEMORY_CARE_CONFIRMED", "SECURED_UNIT_AVAILABLE"} & _must_keys(result)
    assert all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in rows)
    assert all((row.get("care_setting_fit") or {}).get("status") == "PRIMARY_FIT" for row in rows)
    # The memory-care need itself is evaluated against each community's official evidence.
    assert all(str(row.get("memory_care_classification") or "").upper() == "CONFIRMED" for row in rows), [
        (row.get("facility_name"), row.get("memory_care_classification")) for row in rows
    ]
    assert all({"memory_care", "dementia_alz_programs"} <= {n["parameter_id"] for n in row.get("matched_needs") or []} for row in rows)


def test_golden_confirmed_wandering_is_pending_evidence_not_silent_zero_and_never_unconfirmed():
    result = _run_ready(_memory_client("Yes"), _MEMORY_STORY)
    assert {"SECURE_MEMORY_CARE_CONFIRMED", "SECURED_UNIT_AVAILABLE"} <= _must_keys(result)
    state = result["decision_intelligence"]["canonical_decision_state"]
    assert state["client"] == "COMPLETE"
    # The Las Vegas dataset has no verified secured-unit evidence for any community
    # (181 pass the memory-care classification but are unverified for a secured unit):
    # the outcome must be an explicit evidence-pending state, never an unconfirmed row.
    assert result["result_count"] == 0
    assert state["next_action"] == "RESEARCH_PROVIDER_EVIDENCE"
    stage = {item["stage"]: item for item in result["decision_funnel"]["stages"]}["MUST_EVIDENCE_UNKNOWN"]
    assert stage["zeroing_parameter"] == "SECURED_UNIT_AVAILABLE"


def test_golden_skilled_nursing_client_does_not_surface_residential_only_settings():
    result = _run_ready(
        {
            "relationship": "Dad",
            "ageGroup": "80-84",
            "assistanceLevel": "Requires 24/7 nursing care",
            "memoryStatus": "No",
            "budget": 12000,
            "locationCity": "Las Vegas",
        },
        (
            "My father requires 24/7 skilled nursing and ongoing clinical monitoring in Las Vegas. "
            "This is not only help with bathing or dressing; he requires a skilled nursing facility. "
            "His monthly budget is $12,000."
        ),
    )
    rows = result.get("results") or []
    assert rows, result
    assert all(row.get("canonical_type") == "SKILLED_NURSING" for row in rows), [
        (row.get("facility_name"), row.get("canonical_type"), row.get("care_setting_fit")) for row in rows
    ]
    assert all((row.get("care_setting_fit") or {}).get("status") == "PRIMARY_FIT" for row in rows)
    assert all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in rows)


def test_golden_90yo_recent_widow_social_music_case_is_stable_across_ai_preference_variance():
    query = (
        "My mother is 90. Her husband died two months ago and she does not want to remain alone at home. "
        "She needs help with showering, dressing and medication management, but otherwise functions independently. "
        "She loves classical music and being around people. We are looking for an appropriate place in the Las Vegas Valley. "
        "Her monthly budget is $8,000. She has no dementia or memory concerns."
    )
    base = {
        "relationship": "My mother",
        "ageGroup": "90+",
        "assistanceLevel": "Needs assistance with bathing and dressing",
        "memoryStatus": "No",
        "budget": 8000,
        "locationCity": "Las Vegas",
    }
    question = "Would she prefer a larger active community with many people and activities, a smaller intimate setting, or does she have no preference?"
    ai_variants = [
        {"decision_readiness": "READY", "next_question": None, "statements": []},
        {
            "decision_readiness": "NEEDS_CLARIFICATION",
            "next_question": question,
            "statements": [{
                "raw_text": "Community size preference is unknown.",
                "meaning": "Community size is a preference.",
                "importance": "NICE",
                "knowledge_state": "UNKNOWN",
                "status": "ASKED",
                "gap_key": "community_size_preference",
                "mapped_parameters": ["community_size_preference"],
                "clarification_question": question,
                "research_task": None,
            }],
        },
    ]
    unconfigured_variants = []
    for index, ai_result in enumerate(ai_variants):
        with patch.dict(
            os.environ,
            {"OPTIME_CANONICAL_MARKET": "las-vegas", "OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"},
            clear=False,
        ), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai",
            return_value=ai_result,
        ), patch(
            "app.services.must_ai_nice_pipeline.rank_must_eligible_candidates",
            side_effect=_deterministic_rank_for_quality_gate,
        ), patch(
            "app.services.ai_process_owner_guard_patch.attach_ai_process_owner_guarded",
            side_effect=lambda result, questionnaire_state, natural_language_query: result,
        ):
            refresh_runtime_cache(f"golden_90yo_widow_ai_variant_{index}")
            result = run_patient_decision_engine(base, query, limit=5)
        human = result["decision_intelligence"]["human_intelligence"]
        assert result["result_count"] == 5
        assert result["decision_intelligence"]["recommendation_execution_allowed"] is True
        assert human["decision_readiness"] == "READY"
        assert human["adaptive_questions"] == []
        if index == 1:
            assert any(
                row["gap_key"] == "community_size_preference" and row["classification"] == "PREFERENCE"
                for row in human["canonical_gap_policy"]["assessments"]
            )
        unconfigured_variants.append([row.get("facility_name") for row in result["results"]])
    assert unconfigured_variants[0] == unconfigured_variants[1]

    variants = {}
    for preference in ("Large community", "Small community", "No preference"):
        state = dict(base)
        state["humanIntelligenceV2"] = {
            "personalityProfile": {"communitySizePreference": preference},
            "familyProfile": {"socialInteractionNeed": "Very important"},
            "transitionRiskProfile": {"attitudeTowardMove": "Wants to move; does not want to remain alone"},
            "scoringEngine": {"adaptiveSignals": []},
        }
        result = _run_ready(state, query, limit=5)
        rows = result.get("results") or []
        assert len(rows) == 5, result
        assert all(row.get("canonical_type") == "ASSISTED_LIVING_RFG" for row in rows)
        assert all((row.get("care_setting_fit") or {}).get("status") == "PRIMARY_FIT" for row in rows)
        assert all((row.get("client_intent_fit") or {}).get("hard_gate") != "FAIL" for row in rows)
        variants[preference] = [row.get("facility_name") for row in rows]

    assert variants["Large community"] != variants["Small community"]
    print("GOLDEN_90YO_WIDOW_INITIAL_QUESTION=", question)
    print("GOLDEN_90YO_WIDOW_TOP5_VARIANTS=", variants)

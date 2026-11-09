"""Regression: AI may never silently drop recognized facts during repair.

These tests intentionally span arbitrary canonical fields and do not encode
individual clinical therapies or fabricate extracted values.
"""
import pytest

from app.services.semantic_fact_integrity import check_recognized_fact_conservation


def _initial(quote="Dad needs support with bathing.", path="assistanceLevel"):
    return {"statements": [{
        "raw_text": quote, "meaning": "Assistance is required",
        "status": "USED", "knowledge_state": "KNOWN",
        "mapped_parameters": [path],
    }]}


def _final(quote="Dad needs support with bathing.", path="assistanceLevel",
           value="Bathing"):
    return {
        "questionnaire_patch": {path: value},
        "statements": [{
            "raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
            "mapped_parameters": [path],
        }],
    }


def test_recognized_source_field_survives_repair():
    text = "Dad needs support with bathing."
    check_recognized_fact_conservation(
        _initial(), _final(), user_text=text, questionnaire_state={})


def test_mapping_in_trace_without_field_value_must_not_pass():
    final = _final()
    final["questionnaire_patch"] = {}
    with pytest.raises(RuntimeError, match="SEMANTIC_AI_FACT_LOSS.*assistanceLevel"):
        check_recognized_fact_conservation(
            _initial(), final, user_text="Dad needs support with bathing.")


def test_entire_recognized_statement_cannot_disappear():
    with pytest.raises(RuntimeError, match="DROPPED_RECOGNIZED_STATEMENT"):
        check_recognized_fact_conservation(
            _initial(), {"statements": [], "questionnaire_patch": {}},
            user_text="Dad needs support with bathing.")


def test_altered_mapping_cannot_silently_discard_original_fact():
    final = _final(path="memoryStatus", value="Mild forgetfulness")
    with pytest.raises(RuntimeError, match="DROPPED_RECOGNIZED_FIELD:assistanceLevel"):
        check_recognized_fact_conservation(
            _initial(), final, user_text="Dad needs support with bathing.")


def test_explicit_question_preserves_unresolved_fact_without_inventing_value():
    final = {
        "questionnaire_patch": {},
        "statements": [{
            "raw_text": "Dad needs support with bathing.", "status": "ASKED",
            "clarification_question": "What assistance is needed?",
            "knowledge_state": "AMBIGUOUS",
            "mapped_parameters": [],
        }],
    }
    check_recognized_fact_conservation(
        _initial(), final, user_text="Dad needs support with bathing.")


@pytest.mark.parametrize("path,value", [
    ("assistanceLevel", "Bathing"),
    ("medicalCareProfile.needs", ["Dialysis"]),
    ("medicalCareProfile.dialysisFrequency", "three times a week"),
    ("medicalCareProfile.oxygenUse", "At night"),
    ("humanIntelligenceV2.languageProfile.preferredSpokenLanguage", "Hebrew"),
])
def test_integrity_is_domain_independent(path, value):
    quote = "An exact user quote relevant to this field."
    start = _initial(quote=quote, path=path)
    nested = {}
    current = nested
    parts = path.split(".")
    for segment in parts[:-1]:
        current[segment] = {}
        current = current[segment]
    current[parts[-1]] = value
    finish = {"questionnaire_patch": nested, "statements": [{
        "raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
        "mapped_parameters": [path],
    }]}
    check_recognized_fact_conservation(start, finish,
                                        user_text=quote, questionnaire_state={})


def test_existing_questionnaire_selection_can_satisfy_trace():
    initial = _initial()
    final = _final()
    final["questionnaire_patch"] = {}
    check_recognized_fact_conservation(
        initial, final, user_text="Dad needs support with bathing.",
        questionnaire_state={"assistanceLevel": "Bathing"})


def test_unrelated_or_unquoted_statement_is_not_promoted_to_fact():
    initial = _initial(quote="Something not in original text.")
    check_recognized_fact_conservation(
        initial, {"questionnaire_patch": {}, "statements": []},
        user_text="We are asking a general question.", questionnaire_state={})


@pytest.mark.parametrize("placeholder", ["Not sure", "UNKNOWN", "Not specified"])
def test_unknown_value_does_not_falsely_materialize_a_recognized_fact(placeholder):
    finish = _final(value=placeholder)
    with pytest.raises(RuntimeError, match="SEMANTIC_AI_FACT_LOSS.*assistanceLevel"):
        check_recognized_fact_conservation(
            _initial(), finish, user_text="Dad needs support with bathing.")


def test_recognized_research_signal_cannot_silently_disappear():
    original = {"statements": [{
        "raw_text": "The facility's language support has not been verified.",
        "status": "RESEARCH_REQUIRED", "knowledge_state": "UNKNOWN",
        "research_task": "Verify supported languages",
        "mapped_parameters": [],
    }]}
    with pytest.raises(RuntimeError, match="DROPPED_RECOGNIZED_STATEMENT"):
        check_recognized_fact_conservation(
            original, {"statements": [], "questionnaire_patch": {}},
            user_text="The facility's language support has not been verified.")


def test_ambiguous_source_fact_survives_without_fabricated_answer():
    text = "We are unsure whether he needs help transferring."
    original = {"statements": [{
        "raw_text": text, "status": "RESEARCH_REQUIRED",
        "knowledge_state": "AMBIGUOUS", "mapped_parameters": [],
    }]}
    final = {"statements": [{
        "raw_text": text, "status": "ASKED", "knowledge_state": "AMBIGUOUS",
        "clarification_question": "Does he need help transferring?",
        "mapped_parameters": [],
    }], "questionnaire_patch": {}}
    check_recognized_fact_conservation(original, final, user_text=text)


def test_unsupported_nice_mapping_is_preserved_as_unmapped_not_a_verified_fact():
    quote = "The resident wants to keep their vintage piano."
    initial = {"statements": [{
        "raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
        "importance": "NICE", "mapped_parameters": ["relationship"],
    }], "questionnaire_patch": {}}
    final = {"statements": [{
        "raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
        "importance": "NICE", "mapped_parameters": [],
    }], "questionnaire_patch": {}}
    check_recognized_fact_conservation(initial, final, user_text=quote)
    assert final["unmapped_recognized_facts"] == [{
        "raw_text": quote, "rejected_path": "relationship",
        "importance": "NICE",
        "status": "PRESERVED_UNMAPPED_NOT_DECISION_EVIDENCE",
    }]


def test_materialized_must_cannot_disappear_after_repair():
    quote = "Dad needs continuous oxygen."
    initial = {"statements": [{
        "raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
        "importance": "MUST", "mapped_parameters": ["medicalCareProfile.needs"],
    }], "questionnaire_patch": {"medicalCareProfile": {"needs": ["Oxygen"]}}}
    final = {"statements": [{
        "raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
        "importance": "MUST", "mapped_parameters": [],
    }], "questionnaire_patch": {}}
    with pytest.raises(RuntimeError, match="DROPPED_RECOGNIZED_FIELD:medicalCareProfile.needs"):
        check_recognized_fact_conservation(initial, final, user_text=quote)


def test_unmaterialized_must_field_remains_explicitly_unresolved_not_verified():
    quote = "Dad receives dialysis but we do not know the center."
    original = {"statements": [{
        "raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
        "importance": "MUST", "mapped_parameters": ["medicalCareProfile.dialysisCenter"],
    }], "questionnaire_patch": {}}
    result = {"statements": [{
        "raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
        "importance": "MUST", "mapped_parameters": [],
    }], "questionnaire_patch": {}}
    with pytest.raises(RuntimeError, match="DROPPED_RECOGNIZED_FIELD:medicalCareProfile.dialysisCenter"):
        check_recognized_fact_conservation(original, result, user_text=quote)
    assert result["questionnaire_patch"] == {}


def test_unknown_must_detail_can_only_remain_explicitly_unresolved():
    quote = "Dad receives dialysis but we do not know the center."
    original = {"statements": [{
        "raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
        "importance": "MUST", "mapped_parameters": ["medicalCareProfile.dialysisCenter"],
    }], "questionnaire_patch": {}}
    final = {"statements": [{
        "raw_text": quote, "status": "RESEARCH_REQUIRED", "knowledge_state": "UNKNOWN",
        "importance": "MUST", "mapped_parameters": [],
        "research_task": "Verify dialysis center with family.",
    }], "questionnaire_patch": {}}
    check_recognized_fact_conservation(original, final, user_text=quote)
    assert final["questionnaire_patch"] == {}


def test_a_recognized_list_cannot_drop_one_of_two_original_items():
    quote = "Dad needs dialysis and wound care."
    before = {"questionnaire_patch": {
        "medicalCareProfile": {"needs": ["Dialysis", "Wound care"]}
    }, "statements": [{
        "raw_text": quote, "status": "USED", "importance": "MUST",
        "knowledge_state": "KNOWN", "mapped_parameters": ["medicalCareProfile.needs"],
    }]}
    after = {"questionnaire_patch": {
        "medicalCareProfile": {"needs": ["Dialysis"]}
    }, "statements": [{
        "raw_text": quote, "status": "USED", "importance": "MUST",
        "knowledge_state": "KNOWN", "mapped_parameters": ["medicalCareProfile.needs"],
    }]}
    with pytest.raises(RuntimeError, match="DROPPED_RECOGNIZED_VALUE:medicalCareProfile.needs"):
        check_recognized_fact_conservation(before, after, user_text=quote)


def test_reordered_recognized_items_are_not_false_missing_facts():
    quote = "Dad needs dialysis and wound care."
    def packet(items):
        return {"questionnaire_patch": {"medicalCareProfile": {"needs": items}},
                "statements": [{
                    "raw_text": quote, "status": "USED", "importance": "MUST",
                    "knowledge_state": "KNOWN", "mapped_parameters": ["medicalCareProfile.needs"],
                }]}
    check_recognized_fact_conservation(
        packet(["Dialysis", "Wound care"]),
        packet(["Wound care", "Dialysis", "Oxygen"]),
        user_text=quote)

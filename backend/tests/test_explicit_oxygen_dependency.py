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

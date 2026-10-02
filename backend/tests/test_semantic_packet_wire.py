"""Cross-case extraction and clarification contracts at the live boundary."""
import copy

import pytest

from app.services.semantic_intent_ai import (
    _required_output_schema, _validate_patch_contract, _validate_result,
    _question_reasks_answered_dimension, interpret_client_intent_with_ai,
)
from app.services.semantic_packet_wire import normalize_wire, parse_wire_json, provider_schema


def wire():
    return {"wire_version": "semantic-extraction-v1", "facts": [], "preferences": [],
            "constraints": [], "concerns": [], "implications": [], "statements": [],
            "research_requests": [], "questionnaire_patch_fields": {
                path: None for path in provider_schema(_required_output_schema())["$defs"]["PatchFields"]["properties"]},
            "interview": {"readiness": "READY", "next_question": None, "blocking_statement": None}}


def trace(raw, paths=(), **overrides):
    result = {"raw_text": raw, "meaning": raw, "importance": "MUST",
              "knowledge_state": "KNOWN", "status": "USED", "gap_key": None,
              "mapped_parameters": list(paths), "research_task": None}
    result.update(overrides)
    return result


def clarify(packet, question="Which daily tasks require assistance?", path="assistanceLevel"):
    packet["interview"] = {"readiness": "NEEDS_CLARIFICATION", "next_question": question,
        "blocking_statement": {"raw_text": "daily assistance", "meaning": "Tasks remain unclear",
            "importance": "MUST", "knowledge_state": "UNKNOWN", "gap_key": "adl_support",
            "mapped_parameters": [path]}}
    return packet


def normalize(packet):
    # Convert readable test entries into the provider's unique field slots.
    for entry in packet.pop("test_entries", []):
        packet["questionnaire_patch_fields"][entry["path"]] = {
            "value": entry["value"], **({"quote": entry["quote"]} if "quote" in entry else {})}
    return normalize_wire(packet, _required_output_schema())


def test_couple_clarification_preserves_known_partners_and_ai_authored_question():
    text = "He needs daily assistance; she is fully independent."
    packet = clarify(wire())
    packet["test_entries"] = [{"path": "coupleAssistance", "value": text, "quote": text}]
    packet["statements"] = [trace(text, ["coupleAssistance"])]
    result = normalize(packet)
    _validate_patch_contract(result, text, {"relationship": "Couple"})
    assert _validate_result(result)["next_question"] == packet["interview"]["next_question"]
    assert result["questionnaire_patch"]["coupleAssistance"] == text
    assert result["statements"][-1]["clarification_question"] == result["next_question"]
    assert result["statements"][0]["knowledge_state"] == "KNOWN"


@pytest.mark.parametrize("missing", ["next_question", "blocking_statement"])
def test_clarification_cannot_omit_question_or_gap_trace(missing):
    packet = clarify(wire())
    del packet["interview"][missing]
    with pytest.raises(RuntimeError, match="SEMANTIC_AI_WIRE_CONTRACT"):
        normalize(packet)


@pytest.mark.parametrize("entry", [
    {"path": "constraints", "value": ["Building lift"], "quote": "lift"},
    {"path": "medicalCareProfile.transferAssistance", "value": 123, "quote": "lift"},
    {"path": "budget", "value": "6000", "quote": "$6000"},
    {"path": "humanIntelligenceV2.languageProfile.languageNeedScope", "value": "Preference"},
])
def test_illegal_fields_types_and_missing_quotes_are_rejected(entry):
    packet = wire()
    packet["test_entries"] = [entry]
    with pytest.raises(RuntimeError, match="SEMANTIC_AI_WIRE_CONTRACT"):
        normalize(packet)


def test_building_lift_remains_a_requirement_without_inventing_transfer_assistance():
    text = "The building must have a lift because stairs are difficult."
    packet = wire()
    packet["constraints"] = [text]
    packet["statements"] = [trace(text)]
    result = normalize(packet)
    assert result["constraints"] == [text]
    assert result["questionnaire_patch"] == {}
    _validate_patch_contract(result, text, {})


def test_quote_presence_does_not_bypass_exact_quote_validator():
    packet = wire()
    packet["test_entries"] = [{"path": "budget", "value": 6000, "quote": "$6000"}]
    packet["statements"] = [trace("$6000", ["budget"])]
    with pytest.raises(RuntimeError, match="NO_EXACT_FIELD_QUOTE:budget"):
        _validate_patch_contract(normalize(packet), "I haven't chosen a budget.", {})


def test_duplicate_fields_fail_instead_of_overwriting_evidence():
    with pytest.raises(RuntimeError, match="DUPLICATE_MEMBER:budget"):
        parse_wire_json('{"questionnaire_patch_fields":{"budget":{"value":6000,"quote":"$6000"},"budget":{"value":7000,"quote":"$7000"}}}')


def test_multiple_manual_adl_choices_survive_wire_format():
    value = "Help with bathing, Help with dressing"
    packet = wire()
    packet["test_entries"] = [{"path": "assistanceLevel", "value": value.split(", "), "quote": value}]
    assert normalize(packet)["questionnaire_patch"]["assistanceLevel"] == value
    packet["questionnaire_patch_fields"]["assistanceLevel"]["value"] = value
    assert normalize(packet)["questionnaire_patch"]["assistanceLevel"] == value


def test_established_manual_values_are_not_rejected_by_advisory_prompt_examples():
    packet = wire()
    packet["test_entries"] = [
        {"path": "assistanceLevel", "value": "Needs help with bathing and dressing", "quote": "help with bathing and dressing"},
        {"path": "humanIntelligenceV2.transitionRiskProfile.temporarySupportMonths", "value": 3, "quote": "three months"},
    ]
    result = normalize(packet)
    assert result["questionnaire_patch"]["assistanceLevel"] == "Needs help with bathing and dressing"
    assert result["questionnaire_patch"]["humanIntelligenceV2"]["transitionRiskProfile"]["temporarySupportMonths"] == "3"
    _validate_patch_contract(result, "Needs help with bathing and dressing for three months", {})


def test_button_selections_prevent_reasking_exact_resolved_field():
    packet = normalize(clarify(wire()))
    state = {"relationship": "Couple", "assistanceLevel": "Help with bathing, Help with dressing"}
    assert _question_reasks_answered_dimension(packet, state)
    packet["next_question"] = "באילו פעולות יומיומיות צריך עזרה?"
    assert _question_reasks_answered_dimension(packet, state)
    # A broad answer or an unknown is not evidence that these tasks are known.
    assert not _question_reasks_answered_dimension(packet, {"assistanceLevel": "Light assistance"})
    assert not _question_reasks_answered_dimension(packet, {"assistanceLevel": "Not sure"})
    conflict = copy.deepcopy(packet)
    conflict["statements"][-1]["knowledge_state"] = "AMBIGUOUS"
    assert not _question_reasks_answered_dimension(conflict, state)


def test_answered_task_does_not_suppress_different_missing_transfer_need():
    packet = normalize(clarify(wire(), "How much help is needed to transfer?", "medicalCareProfile.transferAssistance"))
    assert not _question_reasks_answered_dimension(packet, {"assistanceLevel": "Help with bathing"})


def test_budget_placeholder_does_not_suppress_a_needed_budget_question():
    packet = normalize(clarify(wire(), "What monthly budget should we use?", "budget"))
    assert not _question_reasks_answered_dimension(packet, {"budget": 0})
    assert not _question_reasks_answered_dimension(packet, {"budget": None})
    assert _question_reasks_answered_dimension(packet, {"budget": 6000})


def test_facility_unknown_becomes_research_and_does_not_ask_family_to_prove_service():
    packet = wire()
    packet["statements"] = [trace("kosher meals", knowledge_state="UNKNOWN",
        status="RESEARCH_REQUIRED", gap_key="kosher_service", research_task="Verify facility kosher meal service")]
    packet["research_requests"] = ["Verify facility kosher meal service"]
    packet["interview"]["readiness"] = "NEEDS_RESEARCH"
    result = _validate_result(normalize(packet))
    assert result["decision_readiness"] == "READY"
    assert result["next_question"] is None
    assert result["statements"][0]["status"] == "RESEARCH_REQUIRED"
    assert result["statements"][0]["knowledge_state"] == "UNKNOWN"


def test_invalid_wire_gets_one_bounded_repair_not_fabricated_ready(monkeypatch):
    calls = []

    def broken_transport(payload):
        calls.append(payload)
        return normalize(clarify(wire(), question=""))

    monkeypatch.setattr("app.services.semantic_intent_ai._default_transport", broken_transport)
    with pytest.raises(RuntimeError, match="EMPTY_CLIENT_QUESTION"):
        interpret_client_intent_with_ai(user_text="daily assistance",
            questionnaire_state={"budget": 6000, "referenceLocationValue": "Las Vegas"})
    assert len(calls) == 2
    assert "packet_validation_repair" in calls[1]


def test_provider_schema_has_closed_objects_and_required_fields():
    schema = provider_schema(_required_output_schema())
    assert schema["type"] == "object"

    def inspect(value):
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value["additionalProperties"] is False
                assert set(value["required"]) == set(value["properties"])
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)
    inspect(schema)


@pytest.mark.parametrize("detail,need,value", [
    ("dialysisFrequency", "Dialysis", "three times weekly"),
    ("oxygenUse", "Oxygen", "At night"),
    ("woundCareFrequency", "Wound care", "daily"),
])
def test_clinical_detail_cannot_silently_lose_its_explicit_parent_need(detail, need, value):
    path = f"medicalCareProfile.{detail}"
    packet = wire()
    packet["test_entries"] = [{"path": path, "value": value, "quote": value}]
    packet["statements"] = [trace(value, [path])]
    result = normalize(packet)
    with pytest.raises(RuntimeError, match="MEDICAL_DETAIL_WITHOUT_NEED"):
        _validate_patch_contract(result, value, {})
    # A button-selected need already satisfies the dependency: no duplicate fact.
    _validate_patch_contract(result, value, {"medicalCareProfile": {"needs": [need]}})
    assert "needs" not in result["questionnaire_patch"]["medicalCareProfile"]

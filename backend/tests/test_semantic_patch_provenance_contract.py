from unittest.mock import patch

import pytest

from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
from app.services.semantic_intent_ai import _validate_patch_contract, interpret_client_intent_with_ai


@pytest.fixture(autouse=True)
def learning_center():
    with patch("app.services.semantic_intent_ai.build_learning_center_advice", return_value={
        "advisor": "test", "available_agent_count": 0, "agent_count": 0,
    }):
        yield


def test_full_field_path_is_required_even_with_a_real_quote():
    packet = {"questionnaire_patch": {"transferAssistance": "One person"},
              "statements": [{"raw_text": "one person", "mapped_parameters": ["transferAssistance"]}]}
    with pytest.raises(RuntimeError, match="OUT_OF_SCHEMA:transferAssistance"):
        _validate_patch_contract(packet, "Needs one person to help.", {})


def test_parent_trace_does_not_authorize_unquoted_medical_leaves():
    packet = {"questionnaire_patch": {"medicalCareProfile": {"needs": ["Dialysis"]}},
              "statements": [{"raw_text": "dialysis", "mapped_parameters": ["medicalCareProfile"]}]}
    with pytest.raises(RuntimeError, match="NO_EXACT_FIELD_QUOTE:medicalCareProfile.needs"):
        _validate_patch_contract(packet, "He needs dialysis.", {})


def test_a_valid_trace_is_not_lost_behind_an_ungrounded_paraphrase():
    path = "medicalCareProfile.transferAssistance"
    packet = {"questionnaire_patch": {"medicalCareProfile": {"transferAssistance": "One person"}},
              "statements": [
                  {"raw_text": "requires transfer support", "mapped_parameters": [path], "knowledge_state": "AMBIGUOUS"},
                  {"raw_text": "one person to help", "mapped_parameters": [path], "knowledge_state": "KNOWN"}]}
    profile = build_structured_profile({}, packet, family_text="She needs one person to help.")
    assert profile["fields"][path]["quote"] == "one person to help"
    assert materialize_questionnaire(profile)["medicalCareProfile"]["transferAssistance"] == "One person"


def test_direct_field_sources_keep_exact_quote_requirement_and_ambiguity():
    path = "medicalCareProfile.transferAssistance"
    packet = {"questionnaire_patch": {"medicalCareProfile": {"transferAssistance": "One person"}},
              "questionnaire_patch_sources": {path: "one person to help"}, "statements": []}
    source = "She needs one person to help."
    _validate_patch_contract(packet, source, {})
    assert materialize_questionnaire(build_structured_profile({}, packet, family_text=source))["medicalCareProfile"]["transferAssistance"] == "One person"
    packet["statements"] = [{"raw_text": "unclear transfer arrangement", "mapped_parameters": [path], "knowledge_state": "AMBIGUOUS"}]
    assert "transferAssistance" not in materialize_questionnaire(build_structured_profile({}, packet, family_text=source)).get("medicalCareProfile", {})
    assert build_structured_profile({}, packet, family_text=source)["fields"][path]["state"] == "UNCLEAR"
    packet["questionnaire_patch_sources"][path] = "an invented quote"
    with pytest.raises(RuntimeError, match="NO_EXACT_FIELD_QUOTE"):
        _validate_patch_contract(packet, source, {})


def test_live_transport_repairs_invalid_field_trace_once():
    source = "She needs one person to help in Las Vegas. Budget $7000."
    path = "medicalCareProfile.transferAssistance"
    invalid = {"decision_readiness": "READY", "questionnaire_patch": {"transferAssistance": "One person"},
               "statements": [{"raw_text": "one person to help", "mapped_parameters": ["transferAssistance"],
                               "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED"}]}
    valid = {"decision_readiness": "READY", "questionnaire_patch": {"medicalCareProfile": {"transferAssistance": "One person"}},
             "statements": [{"raw_text": "one person to help", "mapped_parameters": [path],
                             "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED"}]}
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=[invalid, valid]) as transport:
        packet = interpret_client_intent_with_ai(user_text=source, questionnaire_state={"referenceLocationValue": "Las Vegas", "budget": 7000})
    assert transport.call_count == 2
    assert "OUT_OF_SCHEMA:transferAssistance" in transport.call_args.args[0]["packet_validation_repair"]["validation_error"]
    assert packet["packet_validation_repair"]["attempts"] == 1
    assert materialize_questionnaire(build_structured_profile({}, packet, family_text=source))["medicalCareProfile"]["transferAssistance"] == "One person"


def test_repair_does_not_accept_an_invented_quote():
    invalid = {"decision_readiness": "READY", "questionnaire_patch": {"medicalCareProfile": {"needs": ["Dialysis"]}},
               "statements": [{"raw_text": "needs dialysis", "mapped_parameters": ["medicalCareProfile.needs"],
                               "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED"}]}
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=[invalid, invalid]) as transport:
        with pytest.raises(RuntimeError, match="NO_EXACT_FIELD_QUOTE"):
            interpret_client_intent_with_ai(user_text="He lives in Las Vegas. Budget $7000.", questionnaire_state={"referenceLocationValue": "Las Vegas", "budget": 7000})
    assert transport.call_count == 2


def test_shadow_live_reports_every_case_after_an_interpreter_failure(monkeypatch, capsys):
    import backend.gold_examples.validate_structured_profile_shadow_live as gate
    from app.database import Base

    monkeypatch.setattr(Base.metadata, "create_all", lambda **_: None)
    monkeypatch.setattr(gate, "CASES", {
        "bad": {"questionnaire": {}, "query": "first"},
        "good": {"questionnaire": {}, "query": "second"},
    })
    monkeypatch.setattr(gate, "legacy_regex_profile", lambda *_: {"needs": []})
    monkeypatch.setattr(gate, "build_patient_needs_profile", lambda *_: {"needs": []})
    with patch.object(gate, "interpret_client_intent_with_ai", side_effect=[
        RuntimeError("invalid source quote"), {"questionnaire_patch": {}, "statements": []},
    ]) as transport:
        with pytest.raises(SystemExit) as exit_status:
            gate.main()
    assert exit_status.value.code == 1
    assert transport.call_count == 2
    import json
    report = json.loads(capsys.readouterr().out.split("::error", 1)[0])
    assert report["blocking"] == 1
    assert [case["pass"] for case in report["cases"]] == [False, True]
    assert report["cases"][0]["interpreter_error"] == "invalid source quote"

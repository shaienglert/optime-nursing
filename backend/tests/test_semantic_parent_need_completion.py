"""A detail field whose own quote names the need completes the missing parent need.
Without the word in the quote nothing is inferred and the contract still rejects."""
from app.services.semantic_intent_ai import _complete_stated_parent_needs


def _packet(detail_quote):
    return {
        "questionnaire_patch": {"medicalCareProfile": {"oxygenUse": "At night"}},
        "questionnaire_patch_sources": {"medicalCareProfile.oxygenUse": detail_quote},
    }


def test_quote_that_names_oxygen_completes_the_need():
    text = "Mom is 90. He uses oxygen at night."
    packet = _packet("He uses oxygen at night.")
    _complete_stated_parent_needs(packet, text)
    assert packet["questionnaire_patch"]["medicalCareProfile"]["needs"] == ["Oxygen"]
    assert packet["questionnaire_patch_sources"]["medicalCareProfile.needs"] == "He uses oxygen at night."


def test_quote_without_the_word_infers_nothing():
    text = "He needs a machine at night."
    packet = _packet("He needs a machine at night.")
    _complete_stated_parent_needs(packet, text)
    assert "needs" not in packet["questionnaire_patch"]["medicalCareProfile"]


def test_quote_not_in_the_family_text_infers_nothing():
    packet = _packet("He uses oxygen at night.")
    _complete_stated_parent_needs(packet, "Something else entirely.")
    assert "needs" not in packet["questionnaire_patch"]["medicalCareProfile"]


def test_existing_needs_are_kept_and_not_duplicated():
    text = "He uses oxygen at night and has wound care."
    packet = _packet("He uses oxygen at night")
    packet["questionnaire_patch"]["medicalCareProfile"]["needs"] = ["Wound care", "Oxygen"]
    _complete_stated_parent_needs(packet, text)
    assert packet["questionnaire_patch"]["medicalCareProfile"]["needs"] == ["Wound care", "Oxygen"]


def test_unknown_or_uncertain_detail_never_establishes_the_need():
    text = "Not sure whether oxygen is used."
    packet = _packet(text)
    packet["questionnaire_patch"]["medicalCareProfile"]["oxygenUse"] = "Not sure"
    _complete_stated_parent_needs(packet, text)
    assert "needs" not in packet["questionnaire_patch"]["medicalCareProfile"]
    packet = _packet(text)
    packet["statements"] = [{"raw_text": text, "knowledge_state": "AMBIGUOUS"}]
    _complete_stated_parent_needs(packet, text)
    assert "needs" not in packet["questionnaire_patch"]["medicalCareProfile"]

"""Oxygen parent need requires a genuine explicitly sourced therapy statement."""
from copy import deepcopy

import pytest

from app.services.semantic_intent_ai import _ground_clinical_patch


def _packet(quote, text="He uses oxygen at night."):
    return {
        "questionnaire_patch": {"medicalCareProfile": {"oxygenUse": "At night"}},
        "questionnaire_patch_sources": {"medicalCareProfile.oxygenUse": quote},
        "statements": [{
            "raw_text": quote, "knowledge_state": "KNOWN", "status": "USED",
            "importance": "MUST",
            "mapped_parameters": ["medicalCareProfile.oxygenUse"],
        }],
    }


def test_explicit_night_oxygen_materializes_parent_with_same_source_trace():
    packet = _packet("He uses oxygen at night.")
    normalized = _ground_clinical_patch(packet, "He uses oxygen at night.", {})
    assert normalized["questionnaire_patch"]["medicalCareProfile"]["needs"] == ["Oxygen"]
    assert normalized["questionnaire_patch_sources"]["medicalCareProfile.needs"] == "He uses oxygen at night."
    assert "medicalCareProfile.needs" in normalized["statements"][0]["mapped_parameters"]


def test_sparse_parent_is_merged_without_erasing_other_clinical_needs():
    packet = _packet("He uses oxygen at night.")
    packet["questionnaire_patch"]["medicalCareProfile"]["needs"] = ["Dialysis"]
    normalized = _ground_clinical_patch(packet, "He uses oxygen at night.", {})
    assert normalized["questionnaire_patch"]["medicalCareProfile"]["needs"] == ["Dialysis", "Oxygen"]


@pytest.mark.parametrize("quote,text", [
    ("He uses oxygen at night.", "Another person uses oxygen at night."),
    ("He does not use oxygen at night.", "He does not use oxygen at night."),
    ("We asked about oxygen at night.", "We asked about oxygen at night."),
])
def test_unsupported_or_negated_quotes_do_not_create_oxygen_need(quote, text):
    packet = _packet(quote, text)
    normalized = _ground_clinical_patch(packet, text, {})
    assert "needs" not in normalized["questionnaire_patch"]["medicalCareProfile"]


def test_explicit_dialysis_and_wound_care_are_preserved_without_invented_wound_frequency():
    quote = "Dad receives dialysis three times a week and needs wound care."
    packet = {
        "questionnaire_patch": {"medicalCareProfile": {"woundCareFrequency": "Not specified"}},
        "questionnaire_patch_sources": {"medicalCareProfile.woundCareFrequency": quote},
        "statements": [
            {"raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
             "mapped_parameters": ["medicalCareProfile.needs", "medicalCareProfile.dialysisFrequency"]},
            {"raw_text": quote, "status": "USED", "knowledge_state": "KNOWN",
             "mapped_parameters": ["medicalCareProfile.needs", "medicalCareProfile.woundCareFrequency"]},
        ],
    }
    normalized = _ground_clinical_patch(packet, quote, {})
    medical = normalized["questionnaire_patch"]["medicalCareProfile"]
    assert medical["needs"] == ["Dialysis", "Wound care"]
    assert medical["dialysisFrequency"] == "three times a week"
    assert "woundCareFrequency" not in medical
    assert normalized["questionnaire_patch_sources"]["medicalCareProfile.needs"] == quote
    assert normalized["questionnaire_patch_sources"]["medicalCareProfile.dialysisFrequency"] == quote
    assert all("medicalCareProfile.woundCareFrequency" not in t["mapped_parameters"]
               for t in normalized["statements"])


@pytest.mark.parametrize("text", [
    "Dad does not need wound care or dialysis.",
    "Does Dad need wound care and dialysis?",
    "Dad used to receive dialysis but no longer does.",
])
def test_unproven_clinical_needs_are_not_materialized(text):
    packet = {
        "questionnaire_patch": {"medicalCareProfile": {}},
        "questionnaire_patch_sources": {},
        "statements": [{"raw_text": text, "status": "USED", "knowledge_state": "KNOWN",
                        "mapped_parameters": []}],
    }
    normalized = _ground_clinical_patch(packet, text, {})
    assert "needs" not in normalized["questionnaire_patch"]["medicalCareProfile"]


def test_nonmatching_source_quote_cannot_add_wound_care():
    packet = {
        "questionnaire_patch": {"medicalCareProfile": {}},
        "questionnaire_patch_sources": {},
        "statements": [{"raw_text": "She needs wound care.", "status": "USED",
                        "knowledge_state": "KNOWN", "mapped_parameters": []}],
    }
    assert "needs" not in _ground_clinical_patch(packet, "Dad walks independently.", {})["questionnaire_patch"]["medicalCareProfile"]

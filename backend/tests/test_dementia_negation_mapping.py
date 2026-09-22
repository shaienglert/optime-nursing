"""Explicit denials of dementia must not create a memory-care need.

Found in a live run: "Neither has dementia." (a couple case) produced
memory_care HIGH/YES, which pushes a couple where nobody has dementia toward
memory-care settings.
"""
from __future__ import annotations

import pytest

from app.services.decision_engine_core import build_patient_needs_profile


def _memory(text: str):
    needs = {n["parameter_id"]: n for n in build_patient_needs_profile({}, text)["needs"]}
    return needs.get("memory_care")


@pytest.mark.parametrize("text", [
    "Neither has dementia.",
    "My parents are both 82. Neither has dementia.",
    "Neither of them has dementia or memory problems.",
    "She does not have dementia.",
    "He doesn't have Alzheimer's.",
    "He has no dementia diagnosis.",
    "She has never been diagnosed with dementia.",
    "No signs of dementia.",
])
def test_denied_dementia_is_not_a_positive_memory_care_need(text):
    need = _memory(text)
    assert need is None or need["desired_value"] != "YES", need


@pytest.mark.parametrize("text", [
    "My mother has Alzheimer's and wanders at night.",
    "He has dementia and needs a secure memory care setting.",
    "No one noticed her dementia until last year.",
    "My father does not have dementia. My mother has dementia.",
    "My mother has dementia. My father does not have dementia.",
    "Neither has dementia, but they need memory care for another condition.",
])
def test_stated_dementia_still_creates_memory_care_need(text):
    need = _memory(text)
    assert need is not None and need["desired_value"] == "YES" and need["requirement_level"] == "HIGH", need

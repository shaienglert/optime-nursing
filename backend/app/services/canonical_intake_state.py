from __future__ import annotations

"""Canonicalize explicit intake identity facts before any decision layer reads them.

This module normalizes vocabulary; it does not infer a household, care need, or
relationship from narrative text.  Structured facts remain authoritative and an
explicit gender is never overwritten by a relationship-derived value.
"""

import re
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional, Union


_RELATIONSHIP_ALIASES = {
    "mom": ("Mom", "Female"),
    "mother": ("Mom", "Female"),
    "my mom": ("Mom", "Female"),
    "my mother": ("Mom", "Female"),
    "dad": ("Dad", "Male"),
    "father": ("Dad", "Male"),
    "my dad": ("Dad", "Male"),
    "my father": ("Dad", "Male"),
    "grandma": ("Grandma", "Female"),
    "grandmother": ("Grandma", "Female"),
    "grandpa": ("Grandpa", "Male"),
    "grandfather": ("Grandpa", "Male"),
    "wife": ("Spouse", "Female"),
    "my wife": ("Spouse", "Female"),
    "husband": ("Spouse", "Male"),
    "my husband": ("Spouse", "Male"),
    "spouse": ("Spouse", ""),
    "my spouse": ("Spouse", ""),
    "myself": ("Myself", ""),
    "self": ("Myself", ""),
    "couple": ("Couple", ""),
    "relative": ("Relative", ""),
    "friend": ("Friend", ""),
}

_GENDER_ALIASES = {
    "male": "Male",
    "man": "Male",
    "female": "Female",
    "woman": "Female",
    "nonbinary": "Nonbinary",
    "non-binary": "Nonbinary",
    "other": "Other",
    "prefer not to say": "Prefer not to say",
}


# One unambiguous monthly amount: optional $, digits with optional thousands commas or a
# decimal part, optional "k", optional monthly marker. Anything else (a distance, words, two
# amounts, a negative) is not read as money and is left exactly as the family wrote it.
_MONEY_TEXT = re.compile(
    r"^\$?\s*(?P<amount>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?P<k>k)?"
    r"\s*(?:/\s*mo(?:nth)?|per\s+month|monthly|a\s+month)?$",
    re.IGNORECASE,
)


def _budget_amount(value: Any) -> Optional[Union[int, float]]:
    if not isinstance(value, str):
        return None
    match = _MONEY_TEXT.match(value.strip())
    if not match:
        return None
    amount = float(match.group("amount").replace(",", ""))
    if match.group("k"):
        amount *= 1000
    return int(amount) if amount == int(amount) else amount


# Legacy/free memory labels all mean the intake's "Significant memory issues" (a memory-care
# need). One vocabulary for every channel, so the strategy, the needs engine and the filters
# can never disagree about whether the resident has a memory-care need.
_MEMORY_STATUS_ALIASES = {
    "dementia": "Significant memory issues",
    "alzheimer": "Significant memory issues",
    "alzheimers": "Significant memory issues",
    "alzheimer's": "Significant memory issues",
    "dementia/alzheimer's": "Significant memory issues",
    "memory care": "Significant memory issues",
    "yes": "Significant memory issues",
}


def canonicalize_intake_state(questionnaire_state: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Return an idempotent copy with explicit identity vocabulary normalized."""

    state: Dict[str, Any] = deepcopy(dict(questionnaire_state or {}))
    raw_relationship = str(state.get("relationship") or "").strip()
    raw_gender = str(state.get("gender") or "").strip()

    relationship, relationship_gender = _RELATIONSHIP_ALIASES.get(
        raw_relationship.casefold(),
        (raw_relationship, ""),
    )
    if relationship:
        state["relationship"] = relationship

    canonical_gender = _GENDER_ALIASES.get(raw_gender.casefold(), raw_gender)
    if canonical_gender:
        state["gender"] = canonical_gender
    elif relationship_gender:
        state["gender"] = relationship_gender

    memory_status = _MEMORY_STATUS_ALIASES.get(str(state.get("memoryStatus") or "").strip().casefold())
    if memory_status:
        state["memoryStatus"] = memory_status

    # availableCapital (one-time funds) is a separate fact from the monthly budget.
    for money_field in ("budget", "availableCapital"):
        amount = _budget_amount(state.get(money_field))
        if amount is not None:
            state[money_field] = amount

    return state

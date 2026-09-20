from __future__ import annotations

"""Canonicalize explicit intake identity facts before any decision layer reads them.

This module normalizes vocabulary; it does not infer a household, care need, or
relationship from narrative text.  Structured facts remain authoritative and an
explicit gender is never overwritten by a relationship-derived value.
"""

from copy import deepcopy
from typing import Any, Dict, Mapping


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

    return state

from __future__ import annotations

"""Shared explicit care denials. Absence of a denial never establishes a need."""
import re

_NEGATED_DEMENTIA = re.compile(
    r"\b(?:neither(?:\s+of\s+them)?\s+(?:has|have|had)|nor\s+(?:has|have|does)"
    r"|(?:does|do|did)\s*n[o']t\s+have|(?:has|have)\s+no|never\s+(?:had|been\s+diagnosed\s+with)"
    r"|not\s+diagnosed\s+with|no\s+(?:signs?|history|diagnosis)\s+of|free\s+of)"
    r"\s+(?:any\s+)?(?:dementia|alzheimer'?s?|memory\s+(?:problems?|issues?|loss))\b"
)


def without_negated_nursing(text: str) -> str:
    """Remove only the denied nursing mention; preserve other positive mentions."""
    return re.sub(
        r"\b(?:no(?:\s+need\s+for)?|without|does\s+not\s+(?:need|require)|doesn't\s+(?:need|require))"
        r"\s+(?:any\s+)?(?:(?:skilled|24/7|24x7|round\s+the\s+clock)\s+)?nursing\b",
        "", str(text or "").lower(),
    )


def extract_care_denials(text: str) -> dict[str, bool]:
    normalized = str(text or "").strip().lower()
    def present(token: str) -> bool:
        return token in normalized
    explicit_independence = any(phrase in normalized for phrase in (
        "fully independent", "completely independent", "independent with bathing",
        "independent with dressing", "independent with toileting", "independent with transfers",
    ))
    no_adl_support = explicit_independence or any(phrase in normalized for phrase in (
        "no adl support", "no help with daily activities", "does not need help with daily activities",
        "doesn't need help with daily activities", "no personal care support",
    ))
    no_medication_support = ((explicit_independence and present("medication")) or any(phrase in normalized for phrase in (
        "no medication support", "no medication assistance", "does not need medication support", "doesn't need medication support",
    )))
    no_memory_support = any(phrase in normalized for phrase in (
        "no dementia", "without dementia", "mentally alert", "cognitively intact", "no memory concerns", "no memory concern",
        "does not need cognitive support", "doesn't need cognitive support", "no cognitive support",
    ))
    # A denial belongs to its own mention, not to every person or requirement
    # in the story. Keep a positive mention elsewhere (including memory care
    # explicitly requested despite no dementia diagnosis).
    memory_text_without_denials = _NEGATED_DEMENTIA.sub("", normalized)
    if memory_text_without_denials != normalized:
        no_memory_support = no_memory_support or not any(
            token in memory_text_without_denials
            for token in ("dementia", "alzheimer", "memory care")
        )
    return {"independent": explicit_independence, "adl": no_adl_support, "medication": no_medication_support, "memory": no_memory_support}

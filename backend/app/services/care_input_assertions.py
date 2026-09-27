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



_NEED_TERMS = {
    "adl": r"(?:help|assistance|support)\\s+with\\s+(?:bathing|dressing|toilet(?:ing)?|daily activities)|(?:bathing|dressing|toilet(?:ing)?)\\s+(?:help|assistance|support)",
    "medication": r"(?:help|assistance|support)\\s+with\\s+(?:medications?|medicines?)|medication\\s+(?:help|assistance|support|management)",
    "memory": r"(?:memory care|cognitive support|dementia support)",
}

def _has_positive_need_outside_denial(normalized: str, domain: str) -> bool:
    pattern = _NEED_TERMS[domain]
    for clause in re.split(r"[.!?;\\n]+|\\bbut\\b|\\bhowever\\b|\\bthough\\b|\\balthough\\b", normalized):
        if not re.search(pattern, clause):
            continue
        if re.search(r"\\b(?:does|do|did)\\s+not\\s+(?:need|require|use)|\\bdoesn't\\s+(?:need|require|use)|\\bno\\s+need\\s+for|\\bnever\\s+needed|\\bwithout\\b", clause):
            continue
        if re.search(r"\\b(?:fully|completely)\\s+independent\\s+with\\b", clause):
            continue
        return True
    return False

def _ordinary_denial(normalized: str, concept_pattern: str) -> bool:
    return re.search(
        rf"\\b(?:(?:does|do|did)\\s+not\\s+(?:need|require|use)|doesn't\\s+(?:need|require|use)|no\\s+need\\s+for|never\\s+needed)\\b[^.!?;\\n]{{0,55}}(?:{concept_pattern})\\b",
        normalized,
    ) is not None

def extract_care_denials(text: str) -> dict[str, bool]:
    normalized = str(text or "").strip().lower()
    def present(token: str) -> bool:
        return token in normalized
    explicit_independence = any(phrase in normalized for phrase in (
        "fully independent", "completely independent", "independent with bathing",
        "independent with dressing", "independent with toileting", "independent with transfers",
    ))
    no_adl_support = (explicit_independence and not _has_positive_need_outside_denial(normalized, "adl")) or _ordinary_denial(normalized, r"(?:adl support|help with (?:bathing|dressing|toilet(?:ing)?|daily activities)|personal care support)") or any(phrase in normalized for phrase in (
        "no adl support", "no help with daily activities", "no personal care support",
    ))
    no_medication_support = ((explicit_independence and present("medication") and not _has_positive_need_outside_denial(normalized, "medication")) or _ordinary_denial(normalized, r"(?:medication support|medication assistance|help with (?:medications?|medicines?))") or any(phrase in normalized for phrase in (
        "no medication support", "no medication assistance",
    )))
    no_memory_support = _ordinary_denial(normalized, r"(?:memory care|cognitive support|dementia support)") or any(phrase in normalized for phrase in (
        "no dementia", "without dementia", "mentally alert", "cognitively intact", "no memory concerns", "no memory concern",
        "no cognitive support",
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

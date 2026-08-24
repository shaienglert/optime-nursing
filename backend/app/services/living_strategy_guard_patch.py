from __future__ import annotations

"""Cross-cutting semantic guard for household composition.

A deceased spouse is bereavement context, not evidence of a current two-resident
household. This patch wraps the living-strategy builder so every caller receives the
same governed household semantics without duplicating special cases in UI or ranking.
"""

import re
from typing import Any, Dict

from app.services import living_strategy_runtime as _runtime


_DECEASED_SPOUSE_PATTERNS = (
    r"\b(?:husband|wife|spouse)\s+(?:died|passed away|has died|is deceased)\b",
    r"\blate\s+(?:husband|wife|spouse)\b",
    r"\bwidow(?:ed)?\b",
    r"\bwidower\b",
    r"\bafter (?:her|his|their) (?:husband|wife|spouse) died\b",
)

_CURRENT_COUPLE_PATTERNS = (
    r"\bmy (?:husband|wife|spouse) and i\b",
    r"\bwe both\b",
    r"\bboth of us\b",
    r"\bboth parents\b",
    r"\ba couple\b",
    r"\bthe couple\b",
    r"\bthey want to live together\b",
    r"\bwant to live together\b",
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _has_any(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def deceased_spouse_without_current_couple(questionnaire_state: Dict[str, Any], natural_language_query: str) -> bool:
    query = _norm(natural_language_query)
    if not query or not _has_any(_DECEASED_SPOUSE_PATTERNS, query):
        return False
    if _has_any(_CURRENT_COUPLE_PATTERNS, query):
        return False
    relationship = _norm(questionnaire_state.get("relationship"))
    # Relationship describes who is searching for whom, not household composition.
    # A user explicitly saying wife/husband/spouse still counts as current-couple
    # evidence unless the same text clearly says that spouse is deceased.
    if relationship in {"wife", "husband", "spouse"} and not _has_any(_DECEASED_SPOUSE_PATTERNS, query):
        return False
    return True


def _strip_couple_only_strategy(strategy: Dict[str, Any]) -> Dict[str, Any]:
    household = strategy.get("household") if isinstance(strategy.get("household"), dict) else {}
    household["type"] = "SINGLE_OR_UNKNOWN"
    household["requires_two_resident_model"] = False
    household["resident_profiles"] = []
    household["bereavement_household_override"] = True
    strategy["household"] = household

    candidates = []
    for candidate in strategy.get("strategy_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        capabilities = {str(value or "").upper() for value in candidate.get("required_capabilities") or []}
        if "COUPLE_CORESIDENCE" in capabilities:
            continue
        candidates.append(candidate)
    strategy["strategy_candidates"] = candidates

    questions = []
    for question in strategy.get("guardian_clarification_candidates") or []:
        if not isinstance(question, dict):
            continue
        if str(question.get("question_key") or "") == "ccrc_entrance_fee_tolerance":
            continue
        questions.append(question)
    strategy["guardian_clarification_candidates"] = questions

    strategy["material_unknowns"] = [
        value for value in strategy.get("material_unknowns") or []
        if str(value or "") != "ccrc_entrance_fee_tolerance"
    ]
    signals = strategy.get("signals") if isinstance(strategy.get("signals"), dict) else {}
    signals["deceased_spouse_detected"] = True
    signals["current_couple_household"] = False
    strategy["signals"] = signals
    strategy["household_governance"] = {
        "status": "BEREAVEMENT_NOT_CURRENT_COUPLE",
        "rule": "References to a deceased spouse never create a current couple/co-residence requirement without separate present-tense couple evidence.",
    }
    return strategy


def build_living_strategy_context_guarded(questionnaire_state: Dict[str, Any], natural_language_query: str = "") -> Dict[str, Any]:
    original = getattr(_runtime, "_optime_original_build_living_strategy_context", None)
    if not callable(original):
        original = _runtime.build_living_strategy_context
    strategy = original(questionnaire_state, natural_language_query)
    if deceased_spouse_without_current_couple(questionnaire_state, natural_language_query):
        return _strip_couple_only_strategy(strategy)
    return strategy


def install_patch() -> None:
    if getattr(_runtime.build_living_strategy_context, "_optime_bereavement_guard", False):
        return
    original = _runtime.build_living_strategy_context
    _runtime._optime_original_build_living_strategy_context = original

    def guarded(questionnaire_state: Dict[str, Any], natural_language_query: str = "") -> Dict[str, Any]:
        strategy = original(questionnaire_state, natural_language_query)
        if deceased_spouse_without_current_couple(questionnaire_state, natural_language_query):
            return _strip_couple_only_strategy(strategy)
        return strategy

    setattr(guarded, "_optime_bereavement_guard", True)
    _runtime.build_living_strategy_context = guarded


__all__ = [
    "build_living_strategy_context_guarded",
    "deceased_spouse_without_current_couple",
    "install_patch",
]

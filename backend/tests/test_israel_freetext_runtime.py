"""Owner 2026-11-20 live run of 10 complex free-text cases: nothing the family writes is
dropped, the family sees what was understood, localities and budgets are read robustly,
and a psychogeriatric framework is a MUST."""
import os
from unittest import mock

from app.services import israel_results as r
from app.services.israel_must_gates import FAIL, PASS, PENDING, israel_additional_musts, special_unit_gate


def _packet(patch, statements, sources=None):
    return {"questionnaire_patch": {"israelMarket": patch}, "questionnaire_patch_sources": sources or {}, "statements": statements, "next_question": None}


def _run(text, packet, buttons=None):
    env = {"OPTIME_CANONICAL_MARKET": "israel", "OPTIME_SEMANTIC_AI_URL": "http://x", "OPTIME_SEMANTIC_AI_MODEL": "m", "OPTIME_SEMANTIC_AI_API_KEY": "k"}
    with mock.patch.dict(os.environ, env), mock.patch("app.services.semantic_intent_ai.interpret_client_intent_with_ai", return_value=packet):
        return r.interpret({"israelMarket": buttons or {}}, text)


def test_unmapped_requirement_is_shown_and_flagged_never_dropped():
    text = "אבא צריך מסגרת עם חדר כושר טיפולי. אנחנו מכפר סבא."
    packet = _packet(
        {"city": "כפר סבא"},
        [
            {"raw_text": "אבא צריך מסגרת עם חדר כושר טיפולי.", "importance": "MUST", "mapped_parameters": [], "status": "USED", "knowledge_state": "KNOWN"},
            {"raw_text": "אנחנו מכפר סבא.", "importance": "MUST", "mapped_parameters": ["israelMarket.city"], "status": "USED", "knowledge_state": "KNOWN"},
        ],
        {"israelMarket.city": "אנחנו מכפר סבא."},
    )
    state, info = _run(text, packet)
    assert info["not_used"] == [{"text": "אבא צריך מסגרת עם חדר כושר טיפולי.", "importance": "MUST", "importance_he": "חובה"}]
    assert info["unchecked_requirements"] == ["אבא צריך מסגרת עם חדר כושר טיפולי."]
    assert [u["field"] for u in info["understood"]] == ["city"]


def test_two_localities_keep_the_first_and_prefix_is_stripped_from_text():
    text = "סבתא תשושה. אשדוד או אשקלון."
    state, info = _run(text, _packet({"city": "אשדוד או אשקלון"}, [{"raw_text": "אשדוד או אשקלון.", "importance": "MUST", "mapped_parameters": ["israelMarket.city"], "status": "USED"}], {"israelMarket.city": "אשדוד או אשקלון."}))
    assert state["israelMarket"]["city"] == "אשדוד"
    text = 'לא יותר מ-5 ק"מ מקריית שמונה'
    state, info = _run(text, _packet({}, [{"raw_text": text, "importance": "MUST", "mapped_parameters": [], "status": "USED"}]))
    assert state["israelMarket"]["city"] in {"קריית שמונה", "קרית שמונה"}
    assert any(u["field"] == "city" and u["basis"] == "TEXT_LOCALITY_MATCH" for u in info["understood"])


def test_abbreviation_city_is_expanded():
    text = 'אמא 91 פ"ת סיעודית קוד יש.'
    state, _ = _run(text, _packet({"city": 'פ"ת'}, [{"raw_text": text, "importance": "MUST", "mapped_parameters": ["israelMarket.city"], "status": "USED"}], {"israelMarket.city": text}))
    assert state["israelMarket"]["city"] == "פתח תקווה"


def test_budget_without_code_or_welfare_is_private_and_shown_as_inference():
    text = "בחיפה, תקציב עד 18 אלף בחודש."
    packet = _packet({"city": "חיפה", "monthlyBudgetIls": 18000}, [{"raw_text": text, "importance": "MUST", "mapped_parameters": ["israelMarket.city", "israelMarket.monthlyBudgetIls"], "status": "USED"}], {"israelMarket.city": text, "israelMarket.monthlyBudgetIls": text})
    state, info = _run(text, packet)
    assert state["israelMarket"]["fundingPathway"] == "PRIVATE"
    assert {"field": "fundingPathway", "basis": "INFERRED_FROM_BUDGET"}.items() <= next(u for u in info["understood"] if u["field"] == "fundingPathway").items()
    text = "בחיפה, תקציב עד 18 אלף בחודש ויש קוד."
    state, _ = _run(text, _packet({"city": "חיפה", "monthlyBudgetIls": 18000}, [{"raw_text": text, "importance": "MUST", "mapped_parameters": ["israelMarket.city"], "status": "USED"}], {"israelMarket.city": text, "israelMarket.monthlyBudgetIls": text}))
    assert "fundingPathway" not in state["israelMarket"]  # a code mention is never turned into private pay


def test_invalid_packet_is_retried_once():
    good = _packet({"city": "חיפה"}, [{"raw_text": "חיפה", "importance": "MUST", "mapped_parameters": ["israelMarket.city"], "status": "USED"}], {"israelMarket.city": "חיפה"})
    calls = []

    def flaky(**_):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("SEMANTIC_AI_INVALID_STATEMENT:0")
        return good

    env = {"OPTIME_CANONICAL_MARKET": "israel", "OPTIME_SEMANTIC_AI_URL": "http://x", "OPTIME_SEMANTIC_AI_MODEL": "m", "OPTIME_SEMANTIC_AI_API_KEY": "k"}
    with mock.patch.dict(os.environ, env), mock.patch("app.services.semantic_intent_ai.interpret_client_intent_with_ai", side_effect=flaky):
        _, info = r.interpret({"israelMarket": {}}, "חיפה")
    assert len(calls) == 2 and info["status"] == "INTERPRETED"


def test_missing_items_always_come_with_a_question_and_unknown_city_is_named():
    assert r.missing_required({"functionalLevel": "NURSING", "fundingPathway": "PRIVATE", "city": "עיר שלא קיימת"}) == ["city"]
    assert all(r.MISSING_QUESTION_HE[k] for k in ("functionalLevel", "fundingPathway", "city"))


def test_psychogeriatric_is_a_must_checked_against_listed_units():
    musts = israel_additional_musts({"israelMarket": {"specialUnits": ["PSYCHOGERIATRIC"]}})
    assert [m["key"] for m in musts] == ["IL_PSYCHOGERIATRIC_UNIT"]
    row = lambda units: {"registration_status": "REGISTERED", "israel_questionnaire": {"special_units": units}}
    assert special_unit_gate(row(["PSYCHOGERIATRIC"]), "PSYCHOGERIATRIC")[0] == PASS
    assert special_unit_gate(row(["SUPPORTIVE"]), "PSYCHOGERIATRIC")[0] == FAIL
    assert special_unit_gate(row([]), "PSYCHOGERIATRIC")[0] == PENDING  # not answered is not a no
    assert special_unit_gate({"registration_status": "SYNTHETIC"}, "PSYCHOGERIATRIC")[0] == PENDING

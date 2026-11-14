"""Owner-approved Israeli MUSTs (2026-11-14) and ranking-only preferences."""

import json
import os
from unittest import mock

from app.services.canonical_universe import resolve_canonical_universe_path
from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent, intent_rank_key
from app.services.israel_facility_registration import apply_registration, validate_registration
from tests.israel_registration_fixture import REQUIRED_QUESTIONNAIRE, registration

import pytest


@pytest.fixture(autouse=True, scope="module")
def _tables():
    from app.database import Base, engine
    import app.models.facility  # noqa: F401

    Base.metadata.create_all(bind=engine)


RECORDS = {
    r["canonical_id"]: r
    for r in json.loads(resolve_canonical_universe_path("israel").read_text(encoding="utf-8"))["records"]
}
BASE = RECORDS["IL-MOH-237U6"]


def _facility(**answers):
    payload = registration(questionnaire={**REQUIRED_QUESTIONNAIRE, **answers})
    return apply_registration(BASE, validate_registration(payload))


def _intent(**family):
    with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel"}):
        return build_client_intent({"israelMarket": {"functionalLevel": "NURSING", **family}}, "", {}, {})


def _fit(row, intent):
    with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel"}):
        return evaluate_candidate_intent(row, intent)


def test_medical_needs_filter_only_when_the_family_states_them():
    no_vent = _facility(accepts_ventilated="NO")
    assert _fit(no_vent, _intent())["hard_gate"] == "PASS"
    needs = _intent(medicalNeeds=["VENTILATION"])
    assert _fit(no_vent, needs)["hard_gate"] == "FAIL"
    assert _fit(_facility(accepts_ventilated="YES"), needs)["hard_gate"] == "PASS"
    # Facility did not answer: unknown, not a fail.
    assert _fit(_facility(), needs)["hard_gate"] == "PENDING_VERIFICATION"


def test_unregistered_facility_is_pending_for_every_new_must():
    intent = _intent(medicalNeeds=["PEG", "WANDERING"], isCouple=True, partnerSameLevel=True, residentGenders=["FEMALE"])
    fit = _fit(BASE, intent)
    assert fit["hard_gate"] == "PENDING_VERIFICATION"
    assert not fit["must_fail"]


def test_couples():
    same = _intent(isCouple=True, partnerSameLevel=True)
    different = _intent(isCouple=True, partnerSameLevel=False)
    assert _fit(_facility(couples="NO"), same)["hard_gate"] == "FAIL"
    assert _fit(_facility(couples="SAME_LEVEL"), same)["hard_gate"] == "PASS"
    assert _fit(_facility(couples="SAME_LEVEL"), different)["hard_gate"] == "FAIL"
    assert _fit(_facility(couples="MIXED_LEVELS"), different)["hard_gate"] == "PASS"


def test_gender_policy():
    women_only = _facility(gender_policy="WOMEN_ONLY")
    assert _fit(women_only, _intent(residentGenders=["FEMALE"]))["hard_gate"] == "PASS"
    assert _fit(women_only, _intent(residentGenders=["MALE"]))["hard_gate"] == "FAIL"
    assert _fit(women_only, _intent(residentGenders=["FEMALE", "MALE"]))["hard_gate"] == "FAIL"
    assert _fit(_facility(gender_policy="MIXED"), _intent(residentGenders=["MALE"]))["hard_gate"] == "PASS"


def test_community_mismatch_ranks_lower_but_never_hides():
    intent = _intent(community="HAREDI", kashrut="MEHADRIN", shabbat="IMPORTANT")
    haredi = _facility(religious_character="HAREDI", kashrut="MEHADRIN", shabbat="OBSERVED")
    secular = _facility(religious_character="SECULAR", kashrut="NONE", shabbat="NOT")
    silent = _facility()

    fits = {name: _fit(row, intent) for name, row in (("haredi", haredi), ("secular", secular), ("silent", silent))}
    assert all(fit["hard_gate"] == "PASS" for fit in fits.values())
    assert set(fits["haredi"]["nice_match"]) == {"IL_COMMUNITY", "IL_KASHRUT", "IL_SHABBAT"}
    assert set(fits["secular"]["nice_mismatch"]) == {"IL_COMMUNITY", "IL_KASHRUT", "IL_SHABBAT"}
    assert not fits["silent"]["nice_mismatch"] and not fits["silent"]["nice_match"]

    ranked = sorted(
        [("secular", secular), ("silent", silent), ("haredi", haredi)],
        key=lambda item: intent_rank_key({"client_intent_fit": fits[item[0]]}),
    )
    assert [name for name, _ in ranked] == ["haredi", "silent", "secular"]


def test_mixed_facility_fits_secular_and_traditional_only():
    mixed = _facility(religious_character="MIXED")
    assert "IL_COMMUNITY" in _fit(mixed, _intent(community="TRADITIONAL"))["nice_match"]
    assert "IL_COMMUNITY" in _fit(mixed, _intent(community="RELIGIOUS"))["nice_mismatch"]


def test_language_budget_availability_shelter():
    row = _facility(
        staff_languages=["HE", "RU"],
        vacancy_by_level={"NURSING": "WAITLIST"},
        shelter="ROOM",
    )
    row = apply_registration(
        BASE,
        validate_registration(
            registration(
                monthly_price_ils=15000,
                moh_code_agreement="NO",
                questionnaire={
                    **REQUIRED_QUESTIONNAIRE,
                    "payment_tracks": ["PRIVATE"],
                    "staff_languages": ["HE", "RU"],
                    "vacancy_by_level": {"NURSING": "WAITLIST"},
                    "shelter": "ROOM",
                },
            )
        ),
    )
    fit = _fit(
        row,
        _intent(fundingPathway="PRIVATE", monthlyBudgetIls=16000, language="RU", shelterInRoom="IMPORTANT"),
    )
    assert {"IL_LANGUAGE", "IL_BUDGET", "IL_SHELTER"} <= set(fit["nice_match"])
    assert "IL_AVAILABILITY" in fit["nice_mismatch"]
    assert "IL_LANGUAGE" in _fit(row, _intent(language="AR"))["nice_mismatch"]
    assert "IL_BUDGET" in _fit(row, _intent(fundingPathway="PRIVATE", monthlyBudgetIls=12000))["nice_mismatch"]


def test_new_family_answers_survive_the_structured_profile():
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire

    answers = {
        "functionalLevel": "NURSING",
        "medicalNeeds": ["PEG"],
        "isCouple": True,
        "partnerSameLevel": False,
        "residentGenders": ["FEMALE", "MALE"],
        "community": "TRADITIONAL",
        "kashrut": "KOSHER",
        "shabbat": "IMPORTANT",
        "language": "RU",
        "shelterInRoom": "IMPORTANT",
    }
    restored = materialize_questionnaire(build_structured_profile({"israelMarket": answers}))
    assert restored["israelMarket"] == answers

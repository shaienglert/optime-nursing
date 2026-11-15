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
    intent = _intent(medicalNeeds=["PEG", "WANDERING"], isCouple=True, partnerSameLevel=True)
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


def test_no_gender_condition_and_same_gender_care_is_only_a_preference():
    from app.services.israel_must_gates import ISRAEL_MUST_KEYS

    assert not any("GENDER" in key for key in ISRAEL_MUST_KEYS)
    intent = _intent(sameGenderCare="IMPORTANT")
    rows = {"yes": _facility(same_gender_care="YES"), "no": _facility(same_gender_care="NO"), "silent": _facility()}
    fits = {name: _fit(row, intent) for name, row in rows.items()}
    # Never a condition: every facility stays in the results.
    assert all(fit["hard_gate"] == "PASS" for fit in fits.values())
    assert "IL_SAME_GENDER_CARE" in fits["yes"]["nice_match"]
    assert "IL_SAME_GENDER_CARE" in fits["no"]["nice_mismatch"]
    assert "IL_SAME_GENDER_CARE" not in fits["silent"]["nice_match"] + fits["silent"]["nice_mismatch"]
    ranked = sorted(fits, key=lambda name: intent_rank_key({"client_intent_fit": fits[name]}))
    assert ranked == ["yes", "silent", "no"]
    # Not asked by the family: the facility answer changes nothing.
    assert "IL_SAME_GENDER_CARE" not in _fit(rows["no"], _intent())["nice_mismatch"]


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
        "sameGenderCare": "IMPORTANT",
        "community": "TRADITIONAL",
        "kashrut": "KOSHER",
        "shabbat": "IMPORTANT",
        "language": "RU",
        "shelterInRoom": "IMPORTANT",
    }
    restored = materialize_questionnaire(build_structured_profile({"israelMarket": answers}))
    assert restored["israelMarket"] == answers


def test_welfare_and_private_funding_require_the_matching_track():
    welfare_only = _facility(payment_tracks=["MOH_CODE", "WELFARE"])  # no PRIVATE
    private_only = _facility(payment_tracks=["MOH_CODE", "PRIVATE"])
    welfare = _intent(fundingPathway="WELFARE_ASSISTANCE")
    private = _intent(fundingPathway="PRIVATE")
    assert _fit(welfare_only, welfare)["hard_gate"] == "PASS"
    assert _fit(private_only, welfare)["hard_gate"] == "FAIL"
    assert _fit(private_only, private)["hard_gate"] == "PASS"
    assert _fit(welfare_only, private)["hard_gate"] == "FAIL"
    assert _fit(BASE, welfare)["hard_gate"] == "PENDING_VERIFICATION"


def test_distance_ranks_closer_first_and_out_of_range_lower_but_visible():
    from app.services.israel_geo import km_between, locate

    def at(city, **answers):
        row = _facility(**answers)
        row["city"] = city
        row["latitude"] = row["longitude"] = None
        return row

    haifa, tel_aviv, kiryat_ata = at("חיפה"), at("תל אביב - יפו"), at("קרית אתא")
    intent = _intent(city="חיפה", maxDistanceKm=20)
    fits = {name: _fit(row, intent) for name, row in (("haifa", haifa), ("ta", tel_aviv), ("ata", kiryat_ata))}
    assert all(f["hard_gate"] == "PASS" for f in fits.values())
    assert "IL_DISTANCE" in fits["haifa"]["nice_match"] and "IL_DISTANCE" in fits["ata"]["nice_match"]
    assert "IL_DISTANCE" in fits["ta"]["nice_mismatch"]
    assert fits["haifa"]["distance_km"] < fits["ata"]["distance_km"] < fits["ta"]["distance_km"]
    order = sorted(fits, key=lambda n: intent_rank_key({"client_intent_fit": fits[n]}))
    assert order == ["haifa", "ata", "ta"]
    assert 80 < km_between(locate("חיפה"), locate("תל אביב")) < 95

    # "Anywhere in the country": no match/mismatch, closer still first.
    anywhere = _intent(city="חיפה")
    fit_ta, fit_haifa = _fit(tel_aviv, anywhere), _fit(haifa, anywhere)
    assert "IL_DISTANCE" not in fit_ta["nice_mismatch"]
    assert intent_rank_key({"client_intent_fit": fit_haifa}) < intent_rank_key({"client_intent_fit": fit_ta})


def test_unregistered_facility_still_gets_a_distance():
    fit = _fit(BASE, _intent(city="חיפה", maxDistanceKm=500))
    assert fit["distance_km"] is not None
    assert "IL_DISTANCE" in fit["nice_match"]


def _offer(track, room, level, monthly=None, deposit=None):
    return {"track": track, "room_type": room, "level": level, "monthly_from_ils": monthly, "deposit_from_ils": deposit}


def _budget(row, **family):
    fit = _fit(row, _intent(fundingPathway="PRIVATE", **family))
    note = fit["israel_notes"].get("IL_BUDGET", {})
    return fit, note.get("label"), note.get("offer")


def _priced(*offers, **answers):
    return _facility(price_publication="PUBLISH", price_offers=list(offers), **answers)


def test_no_price_is_on_request_and_neutral():
    for row in (_facility(price_publication="WITHHOLD"), _facility(), BASE):
        fit, label, _ = _budget(row, monthlyBudgetIls=15000)
        assert label == "מחיר בבירור"
        assert "IL_BUDGET" in fit["nice_unknown"] and fit["hard_gate"] != "FAIL"


def test_starting_price_at_the_family_level():
    row = _priced(_offer("MONTHLY", "SHARED_2", "NURSING", 14000), _offer("MONTHLY", "SINGLE", "NURSING", 18000))
    fit, label, offer = _budget(row, monthlyBudgetIls=15000)
    assert label == "בתקציב לפי המחיר ההתחלתי" and offer["room_type"] == "SHARED_2"
    fit, label, _ = _budget(row, monthlyBudgetIls=12000)
    assert label == "המחיר ההתחלתי מעל התקציב" and "IL_BUDGET" in fit["nice_mismatch"]
    assert fit["hard_gate"] == "PASS"  # over budget ranks lower, never hides


def test_price_only_for_another_level_may_fit_subject_to_offer():
    row = _priced(_offer("MONTHLY", "SHARED_2", "FRAIL", 9000))
    fit, label, _ = _budget(row, monthlyBudgetIls=15000)  # family needs NURSING
    assert label == "עשוי להתאים לתקציב, בכפוף להצעה" and "IL_BUDGET" in fit["nice_unknown"]


def test_cheapest_room_has_no_place_still_counts_price_but_availability_is_separate():
    row = _priced(
        _offer("MONTHLY", "SHARED_2", "NURSING", 14000),
        vacancy_by_level={"NURSING": "NONE"},
    )
    fit, label, _ = _budget(row, monthlyBudgetIls=15000)
    assert label == "בתקציב לפי המחיר ההתחלתי"
    assert "IL_AVAILABILITY" in fit["nice_mismatch"]


def test_same_monthly_two_tracks_different_deposits_respects_the_deposit_ceiling():
    housing = _priced(
        _offer("DEPOSIT", "APT_2", "NURSING", 6000, 900_000),
        _offer("DEPOSIT", "APT_3", "NURSING", 6000, 1_500_000),
    )
    _, label, offer = _budget(housing, monthlyBudgetIls=8000, depositCapIls=1_000_000)
    assert label == "בתקציב לפי המחיר ההתחלתי" and offer["deposit_from_ils"] == 900_000
    _, label, _ = _budget(housing, monthlyBudgetIls=8000, depositCapIls=500_000)
    assert label == "המחיר ההתחלתי מעל התקציב"
    _, label, _ = _budget(housing, monthlyBudgetIls=8000)  # no ceiling given
    assert label == "בתקציב לפי המחיר ההתחלתי"


def test_deposit_without_maintenance_needs_an_offer():
    housing = _priced(_offer("DEPOSIT", "APT_2", "NURSING", None, 800_000))
    _, label, _ = _budget(housing, monthlyBudgetIls=8000, depositCapIls=1_000_000)
    assert label == "עשוי להתאים לתקציב, בכפוף להצעה"


def test_price_page_texts():
    from app.services.israel_facility_questionnaire import describe_offer

    assert describe_offer(_offer("MONTHLY", "SHARED_2", "FRAIL", 9500)) == "החל מ-₪9,500 לחודש (חדר משותף לשניים, תשושים)"
    assert describe_offer(_offer("DEPOSIT", "APT_2", "INDEPENDENT", 5500, 1_200_000)) == (
        "פיקדון החל מ-₪1,200,000 ודמי אחזקה החל מ-₪5,500 לחודש (דירת 2 חדרים, עצמאיים)"
    )
    assert "דמי האחזקה דורשים בירור" in describe_offer(_offer("DEPOSIT", "APT_2", "INDEPENDENT", None, 900_000))
    assert describe_offer(_offer("MONTHLY", "STUDIO", "INDEPENDENT", 12000, 50_000)).startswith(
        "החל מ-₪12,000 לחודש, עם פיקדון נלווה של ₪50,000"
    )


def test_shelter_as_condition_or_preference():
    room, floor, outside = _facility(shelter="ROOM"), _facility(shelter="FLOOR"), _facility(shelter="NEARBY")
    silent = _facility()

    strict_room = _intent(shelterNeed="ROOM", shelterIsCondition=True)
    assert _fit(room, strict_room)["hard_gate"] == "PASS"
    assert _fit(floor, strict_room)["hard_gate"] == "FAIL"
    assert _fit(silent, strict_room)["hard_gate"] == "PENDING_VERIFICATION"

    strict_floor = _intent(shelterNeed="FLOOR", shelterIsCondition=True)
    assert _fit(floor, strict_floor)["hard_gate"] == "PASS"
    assert _fit(room, strict_floor)["hard_gate"] == "PASS"
    assert _fit(outside, strict_floor)["hard_gate"] == "FAIL"

    preference = _intent(shelterNeed="FLOOR")
    assert _fit(outside, preference)["hard_gate"] == "PASS"
    assert "IL_SHELTER" in _fit(outside, preference)["nice_mismatch"]
    assert "IL_SHELTER" in _fit(floor, preference)["nice_match"]
    assert "IL_SHELTER" in _fit(silent, preference)["nice_unknown"]


def test_bedridden_resident_requires_a_protection_plan():
    intent = _intent(bedridden=True)
    assert _fit(_facility(shelter_bedridden="MOVED_IN_BED"), intent)["hard_gate"] == "PASS"
    assert _fit(_facility(shelter_bedridden="PROTECTED_IN_ROOM"), intent)["hard_gate"] == "PASS"
    assert _fit(_facility(shelter_bedridden="NO_SOLUTION"), intent)["hard_gate"] == "FAIL"
    assert _fit(_facility(shelter_bedridden="NOT_RELEVANT"), intent)["hard_gate"] == "PENDING_VERIFICATION"
    assert _fit(_facility(), intent)["hard_gate"] == "PENDING_VERIFICATION"
    assert _fit(_facility(shelter_bedridden="NO_SOLUTION"), _intent())["hard_gate"] == "PASS"


def test_up_to_ten_percent_over_budget_is_labelled_and_neutral():
    row = _priced(_offer("MONTHLY", "SHARED_2", "NURSING", 16000))
    fit, label, _ = _budget(row, monthlyBudgetIls=15000)  # 6.7% over
    assert label == "מעל התקציב ב-7% (בתוך סטייה של עד 10%)"
    assert "IL_BUDGET" in fit["nice_unknown"] and "IL_BUDGET" not in fit["nice_mismatch"]
    _, label, _ = _budget(row, monthlyBudgetIls=14500)  # 10.3% over
    assert label == "המחיר ההתחלתי מעל התקציב"

    housing = _priced(_offer("DEPOSIT", "APT_2", "NURSING", 6000, 1_080_000))
    _, label, _ = _budget(housing, monthlyBudgetIls=8000, depositCapIls=1_000_000)  # deposit 8% over
    assert label == "מעל התקציב ב-8% (בתוך סטייה של עד 10%)"
    _, label, _ = _budget(housing, monthlyBudgetIls=8000, depositCapIls=0)  # family wants no deposit
    assert label == "המחיר ההתחלתי מעל התקציב"

    # In budget still ranks above within-tolerance.
    within = _fit(_priced(_offer("MONTHLY", "SHARED_2", "NURSING", 14000)), _intent(fundingPathway="PRIVATE", monthlyBudgetIls=15000))
    near = _fit(row, _intent(fundingPathway="PRIVATE", monthlyBudgetIls=15000))
    assert intent_rank_key({"client_intent_fit": within}) < intent_rank_key({"client_intent_fit": near})


def test_lifestyle_preferences_only_rank():
    row = _facility(setting="RURAL", style="HOMEY", day_style="FLEXIBLE", social_atmosphere="QUIET",
                    activities_offered=["GARDENING", "MUSIC"], nurse_24_7="YES", room_types=["SHARED_2"])
    fit = _fit(row, _intent(priority="MEDICAL", setting="RURAL", styles=["HOMEY", "BOUTIQUE"], dayRhythm="FLEXIBLE",
                            activities=["MUSIC", "LECTURES"]))
    assert {"IL_PRIORITY", "IL_SETTING", "IL_STYLE", "IL_DAY_RHYTHM", "IL_ACTIVITIES"} <= set(fit["nice_match"])

    other = _fit(row, _intent(priority="SOCIAL", setting="URBAN", styles=["LUXURY"], dayRhythm="PEOPLE_AROUND",
                              activities=["OUTINGS"]))
    assert other["hard_gate"] == "PASS"  # never hides
    assert {"IL_PRIORITY", "IL_SETTING", "IL_STYLE", "IL_DAY_RHYTHM", "IL_ACTIVITIES"} <= set(other["nice_mismatch"])
    assert "IL_DAY_RHYTHM" in _fit(row, _intent(dayRhythm="PRIVATE_SPACE"))["nice_mismatch"]

    silent = _fit(_facility(setting="SUBURBAN"), _intent(setting="URBAN", activities=["MUSIC"]))
    assert {"IL_SETTING", "IL_ACTIVITIES"} <= set(silent["nice_unknown"])


def _levels(levels, **answers):
    payload = registration(functional_levels_served=levels, questionnaire={**REQUIRED_QUESTIONNAIRE, **answers})
    return apply_registration(BASE, validate_registration(payload))


def test_supportive_unit_serves_frail_residents():
    frail = _intent(functionalLevel="FRAIL")
    assert _fit(_levels(["INDEPENDENT"]), frail)["hard_gate"] == "FAIL"
    assert _fit(_levels(["INDEPENDENT"], special_units=["SUPPORTIVE"]), frail)["hard_gate"] == "PASS"
    # The unit does not stretch to nursing residents.
    assert _fit(_levels(["INDEPENDENT"], special_units=["SUPPORTIVE"]), _intent())["hard_gate"] == "FAIL"


def test_complex_nursing_needs_a_complex_ward_and_never_asks_funding():
    complex_ = _intent(functionalLevel="COMPLEX_NURSING")
    assert not [m for m in complex_["must_haves"] if m["key"] in {"IL_MOH_CODE_AGREEMENT", "IL_FUNDING_TRACK"}]
    assert _fit(_facility(special_units=["COMPLEX_NURSING"]), complex_)["hard_gate"] == "PASS"
    assert _fit(_facility(special_units=["HOSPICE"]), complex_)["hard_gate"] == "FAIL"
    assert _fit(_levels(["INDEPENDENT"]), complex_)["hard_gate"] == "FAIL"
    # A nursing home that left the units question blank is unknown, not excluded.
    assert _fit(_facility(), complex_)["hard_gate"] == "PENDING_VERIFICATION"
    assert _fit(BASE, complex_)["hard_gate"] == "PENDING_VERIFICATION"

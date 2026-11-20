"""The shared AI interpreter's Israeli extraction contract.

These tests replace the model with a fixed wire packet: they prove that what a model
returns is constrained, validated and carried into the same Israeli intent as the
structured questionnaire. They do not measure how well a real model reads Hebrew.
"""

import json
import os
from unittest import mock

import pytest

TEXT = (
    "אני מחפשת מקום לאמא שלי, היא סיעודית לגמרי. יש לנו קוד של משרד הבריאות. "
    "אנחנו גרים בחיפה ולא רוצים יותר מ-20 ק\"מ. אמא מדברת בעיקר רוסית, אנחנו משפחה מסורתית ואוכל כשר חשוב לנו."
)
S1 = "אני מחפשת מקום לאמא שלי, היא סיעודית לגמרי."
S2 = "יש לנו קוד של משרד הבריאות."
S3 = "אנחנו גרים בחיפה ולא רוצים יותר מ-20 ק\"מ."
S4 = "אמא מדברת בעיקר רוסית, אנחנו משפחה מסורתית ואוכל כשר חשוב לנו."


@pytest.fixture(autouse=True)
def israel():
    with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel-synthetic"}):
        from app.database import Base, engine
        import app.main  # noqa: F401  (registers every table)

        Base.metadata.create_all(bind=engine)
        yield


def _trace(raw, paths, importance="MUST"):
    return {"raw_text": raw, "meaning": "m", "importance": importance, "knowledge_state": "KNOWN", "status": "USED",
            "gap_key": None, "mapped_parameters": paths, "research_task": None}


def _wire(fields, statements):
    return {"wire_version": "semantic-extraction-v1", "facts": [], "preferences": [], "constraints": [], "concerns": [],
            "implications": [], "statements": statements, "research_requests": [], "questionnaire_patch_fields": fields,
            "interview": {"readiness": "READY", "next_question": None, "blocking_statement": None}}


FIELDS = [
    {"path": "israelMarket.relationship", "value": "אמא", "quote": S1},
    {"path": "israelMarket.functionalLevel", "value": "NURSING", "quote": S1},
    {"path": "israelMarket.fundingPathway", "value": "MOH_CODE", "quote": S2},
    {"path": "israelMarket.city", "value": "חיפה", "quote": S3},
    {"path": "israelMarket.maxDistanceKm", "value": 20, "quote": S3},
    {"path": "israelMarket.language", "value": "RU", "quote": S4},
    {"path": "israelMarket.community", "value": "TRADITIONAL", "quote": S4},
    {"path": "israelMarket.kashrut", "value": "KOSHER", "quote": S4},
]
STATEMENTS = [
    _trace(S1, ["israelMarket.relationship", "israelMarket.functionalLevel"]),
    _trace(S2, ["israelMarket.fundingPathway"]),
    _trace(S3, ["israelMarket.city", "israelMarket.maxDistanceKm"]),
    _trace(S4, ["israelMarket.language", "israelMarket.community", "israelMarket.kashrut"], "NICE"),
]


def test_israeli_schema_offers_only_israeli_fields_with_closed_vocabularies():
    from app.services.semantic_intent_ai import _required_output_schema
    from app.services.semantic_packet_wire import provider_schema

    required = _required_output_schema()
    assert list(required["questionnaire_patch"]) == ["israelMarket"]
    schema = json.dumps(provider_schema(required, family_text=TEXT, questionnaire_state={}), ensure_ascii=False)
    assert "COGNITIVE_FRAIL" in schema and "WELFARE_ASSISTANCE" in schema
    assert "maximumDistanceMiles" not in schema and "medicalCareProfile" not in schema


def test_contract_rejects_values_outside_the_vocabulary_and_unquoted_units():
    from app.services.semantic_intent_ai import _required_output_schema
    from app.services.semantic_packet_wire import normalize_wire

    required = _required_output_schema()
    bad_level = [dict(FIELDS[1], value="SKILLED_NURSING")]
    with pytest.raises(RuntimeError, match="WIRE_CONTRACT"):
        normalize_wire(_wire(bad_level, STATEMENTS[:1]), required, family_text=TEXT)
    km_without_unit = [{"path": "israelMarket.maxDistanceKm", "value": 20, "quote": S2}]
    with pytest.raises(RuntimeError, match="UNSUPPORTED_UNIT"):
        normalize_wire(_wire(km_without_unit, STATEMENTS[1:2]), required, family_text=TEXT)


def test_a_valid_packet_produces_the_same_intent_as_the_questionnaire():
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
    from app.services.client_intent_runtime import build_client_intent
    from app.services.semantic_intent_ai import _required_output_schema, interpret_client_intent_with_ai
    from app.services.semantic_packet_wire import normalize_wire

    packet = normalize_wire(_wire(FIELDS, STATEMENTS), _required_output_schema(), family_text=TEXT)
    result = interpret_client_intent_with_ai(user_text=TEXT, questionnaire_state={}, transport=lambda _payload: packet)
    state = materialize_questionnaire(build_structured_profile({}, result, family_text=TEXT))

    structured = {"relationship": "אמא", "functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "חיפה",
                  "maxDistanceKm": 20, "language": "RU", "community": "TRADITIONAL", "kashrut": "KOSHER"}
    assert state["israelMarket"] == structured
    from_text = build_client_intent(state, TEXT, {}, {})
    from_form = build_client_intent({"israelMarket": structured}, "", {}, {})
    assert [m["key"] for m in from_text["must_haves"]] == [m["key"] for m in from_form["must_haves"]]
    assert [n["key"] for n in from_text["nice_to_haves"]] == [n["key"] for n in from_form["nice_to_haves"]]


def test_israeli_minimum_dimensions_read_hebrew():
    from app.services.semantic_intent_ai import _minimum_dimension_status

    assert _minimum_dimension_status(TEXT, {}) == {"market_location": True, "monthly_affordability": True}
    assert _minimum_dimension_status("נשלם באופן פרטי עד 16 אלף בחודש, באזור ירושלים.", {}) == {
        "market_location": True, "monthly_affordability": True}
    assert _minimum_dimension_status("אמא סיעודית.", {}) == {"market_location": False, "monthly_affordability": False}


def test_explicit_practical_requirements_survive_extraction_and_need_facility_answers():
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
    from app.services.israel_must_gates import evaluate_israel_must, israel_additional_musts
    from app.services.semantic_intent_ai import _required_output_schema
    from app.services.semantic_packet_wire import normalize_wire

    quote = "We need two bedrooms, a live-in private caregiver, accessible parking, a cat, and gluten-free meals."
    values = {
        "minBedrooms": 2,
        "privateCaregiver": "LIVE_IN",
        "parkingType": "ACCESSIBLE",
        "petRequired": True,
        "requiredDiets": ["GLUTEN_FREE"],
    }
    fields = [{"path": f"israelMarket.{key}", "value": value, "quote": quote} for key, value in values.items()]
    packet = normalize_wire(_wire(fields, [_trace(quote, [item["path"] for item in fields])]), _required_output_schema(), family_text=quote)
    state = materialize_questionnaire(build_structured_profile({}, packet, family_text=quote))
    assert state["israelMarket"] == values
    musts = israel_additional_musts(state)
    assert len(musts) == 5

    answers = {
        "max_bedrooms": 2,
        "private_caregiver_live_in": "AT_ADMISSION",
        "parking_types": ["ACCESSIBLE"],
        "pets": "YES",
        "diets": ["GLUTEN_FREE"],
    }
    row = {"registration_status": "REGISTERED", "israel_questionnaire": answers}
    assert all(evaluate_israel_must(row, must)[0] == "PASS" for must in musts)
    answers.pop("max_bedrooms")
    answers["private_caregiver_live_in"] = "NO"
    outcomes = {must["key"]: evaluate_israel_must(row, must)[0] for must in musts}
    assert outcomes["IL_BEDROOMS"] == "PENDING"
    assert outcomes["IL_PRIVATE_CAREGIVER"] == "FAIL"

    caregiver = next(must for must in musts if must["key"] == "IL_PRIVATE_CAREGIVER")
    answers["private_caregiver_live_in"] = "ONLY_AFTER_ADMISSION"
    answers["private_caregiver_visits"] = "AT_ADMISSION"
    assert evaluate_israel_must(row, caregiver)[0] == "FAIL"
    assert evaluate_israel_must(row, {**caregiver, "value": "VISITS"})[0] == "PASS"
    answers["private_caregiver_live_in"] = "YES"  # Old answer without a known admission policy.
    assert evaluate_israel_must(row, caregiver)[0] == "PENDING"

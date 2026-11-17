"""Israeli results route (owner decision 2026-11-17): only facilities that pass every MUST
are shown, missing information is stated, OOMNIKER never relaxes a MUST, Nevada never
reaches the route."""

import copy
import json
import os
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app.services.canonical_universe import resolve_canonical_universe_path
from app.services.israel_facility_registration import apply_registration, validate_registration
from tests.israel_registration_fixture import REQUIRED_QUESTIONNAIRE, registration


@pytest.fixture(autouse=True, scope="module")
def _tables():
    from app.database import Base, engine
    import app.models.facility  # noqa: F401

    Base.metadata.create_all(bind=engine)


BASE = {
    r["canonical_id"]: r for r in json.loads(resolve_canonical_universe_path("israel").read_text(encoding="utf-8"))["records"]
}["IL-MOH-237U6"]


def _row(cid, name, **reg):
    row = copy.deepcopy(BASE)
    row["canonical_id"], row["facility_name"] = cid, name
    payload = validate_registration(registration(**reg)) if reg is not None else None
    return (apply_registration(row, payload) if payload else row), payload


ROWS = dict(
    PASS_NEAR=_row("T-PASS-NEAR", "עובר", questionnaire={**REQUIRED_QUESTIONNAIRE, "staff_languages": ["HE", "RU"]}),
    PASS_FAR=_row("T-PASS-NOLANG", "עובר בלי רוסית", questionnaire={**REQUIRED_QUESTIONNAIRE, "staff_languages": ["HE"]}),
    FAIL_LEVEL=_row("T-FAIL", "לא מקבל סיעודיים", functional_levels_served=["INDEPENDENT"]),
    NO_CODE=_row("T-NOCODE", "בלי קוד", moh_code_agreement="NO", questionnaire={**REQUIRED_QUESTIONNAIRE, "payment_tracks": ["PRIVATE"]}),
)
UNREGISTERED = copy.deepcopy(BASE)
UNREGISTERED["canonical_id"], UNREGISTERED["facility_name"] = "T-UNREG", "לא נרשם"


def _call(family, market="israel"):
    from app.main import app

    records = [row for row, _ in ROWS.values()] + [UNREGISTERED]
    regs = {row["canonical_id"]: payload for row, payload in ROWS.values()}
    with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": market}), mock.patch(
        "app.services.israel_facility_import.load_israel_records", return_value=(records, None)
    ), mock.patch("app.services.israel_facility_registration.load_israel_registration", side_effect=lambda db, cid: regs.get(cid)):
        return TestClient(app).post("/api/il/recommendations", json={"questionnaire_state": {"israelMarket": family}})


FAMILY = {"functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "חיפה", "language": "RU"}


def test_only_facilities_that_pass_every_must_are_shown_and_ordered():
    body = _call(FAMILY).json()
    assert body["status"] == "OK"
    shown = [c["canonical_id"] for c in body["results"]]
    assert shown == ["T-PASS-NEAR", "T-PASS-NOLANG"]  # language preference orders, never filters
    assert body["funnel"] == {**body["funnel"], "universe": 5, "passed": 2, "failed": 2, "pending": 1}
    first, second = body["results"]
    assert {m["key"] for m in first["musts_met"]} >= {"IL_FUNCTIONAL_LEVEL", "IL_MOH_CODE_AGREEMENT", "LICENSE_CURRENTLY_VALID"}
    assert "IL_LANGUAGE" in [p["key"] for p in first["preferences_met"]]
    assert "IL_LANGUAGE" in [p["key"] for p in second["preferences_not_met"]]
    assert first["source"]["basis"] == "FACILITY_SUPPLIED"
    assert first["rank_key"] <= second["rank_key"]


def test_oomniker_explains_and_never_relaxes_a_must():
    body = _call({**FAMILY, "functionalLevel": "COGNITIVE_FRAIL"}).json()
    assert body["results"] == []
    lines = " ".join(body["oomniker"]["lines"] + body["oomniker"]["actions"])
    assert "אין כרגע מוסד" in lines and "תנאי החובה שלכם לא משתנים" in lines
    assert body["oomniker"]["analysis"]["profile_mutated"] is False
    assert not [s for s in body["oomniker"]["analysis"]["suggestions"] if s.get("action") == "OFFER_PREFERENCE_ALTERNATIVE"]


def test_unclear_level_is_the_familys_question_not_missing_facility_data():
    body = _call({**FAMILY, "functionalLevel": "UNCLEAR"}).json()
    assert body["results"] == []
    assert body["funnel"]["family_unknown"][0]["key"] == "IL_FUNCTIONAL_LEVEL"
    text = " ".join(body["oomniker"]["lines"] + body["oomniker"]["actions"])
    assert "רמת התפקוד עוד לא ברורה" in text
    assert body["funnel"]["pending_on_facility_information"] == 1  # only the unregistered one
    assert all(r["key"] != "IL_FUNCTIONAL_LEVEL" for r in body["funnel"]["pending_reasons"])


def test_missing_required_fact_asks_instead_of_matching():
    body = _call({"functionalLevel": "NURSING", "city": "חיפה"}).json()
    assert body == {**body, "status": "NEEDS_INPUT", "missing": ["fundingPathway"], "results": []}
    complex_nursing = _call({"functionalLevel": "COMPLEX_NURSING", "city": "חיפה"}).json()
    assert complex_nursing["status"] == "OK"  # complex nursing never asks for funding


def test_free_text_without_interpreter_is_marked_unprocessed_not_guessed():
    from app.main import app

    with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel", "OPTIME_SEMANTIC_AI_URL": "", "OPTIME_SEMANTIC_AI_MODEL": ""}), mock.patch(
        "app.services.israel_facility_import.load_israel_records", return_value=([], None)
    ):
        body = TestClient(app).post(
            "/api/il/recommendations",
            json={"questionnaire_state": {"israelMarket": FAMILY, "notes": "אמא מונשמת"}},
        ).json()
    assert body["interpretation"]["status"] == "UNPROCESSED"
    assert "IL_ACCEPTS_VENTILATED" not in [m["key"] for m in body["musts"]]


def test_nevada_never_reaches_the_israeli_route():
    assert _call(FAMILY, market="NV").status_code == 404

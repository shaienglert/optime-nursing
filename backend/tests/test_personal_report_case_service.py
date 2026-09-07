from __future__ import annotations

from app.database import Base, SessionLocal, engine
import app.models.personal_report_case  # noqa: F401 -- registers tables on Base
from app.services.personal_report_case_service import case_inputs, create_case, get_case_by_token, save_snapshot

Base.metadata.create_all(bind=engine)


def _db():
    return SessionLocal()


def test_create_case_round_trips_inputs():
    db = _db()
    try:
        case = create_case(
            db,
            questionnaire_state={"relationship": "Father", "budget": 6000},
            natural_language_query="test query",
            limit=5,
        )
        assert case.case_token
        assert len(case.case_token) == 32  # uuid4 hex, no dashes

        loaded = get_case_by_token(db, case.case_token)
        assert loaded is not None
        assert loaded.id == case.id
        inputs = case_inputs(loaded)
        assert inputs["questionnaire_state"] == {"relationship": "Father", "budget": 6000}
        assert inputs["natural_language_query"] == "test query"
        assert inputs["limit"] == 5
    finally:
        db.close()


def test_case_tokens_are_not_sequential_or_guessable():
    db = _db()
    try:
        case_a = create_case(db, questionnaire_state={}, natural_language_query="", limit=5)
        case_b = create_case(db, questionnaire_state={}, natural_language_query="", limit=5)
        assert case_a.case_token != case_b.case_token
        # Not a trivially incrementable/short token.
        assert case_a.case_token.isalnum()
        assert len(case_a.case_token) >= 32
    finally:
        db.close()


def test_unknown_case_token_returns_none():
    db = _db()
    try:
        assert get_case_by_token(db, "does-not-exist") is None
    finally:
        db.close()


def test_save_snapshot_links_to_case():
    db = _db()
    try:
        case = create_case(db, questionnaire_state={"relationship": "Mother"}, natural_language_query="", limit=5)
        snapshot = save_snapshot(db, case_id=case.id, report_ready=True, report={"user_role": "FAMILY_MEMBER"})
        assert snapshot.case_id == case.id
        assert snapshot.report_ready is True
        assert "FAMILY_MEMBER" in snapshot.report_json
    finally:
        db.close()

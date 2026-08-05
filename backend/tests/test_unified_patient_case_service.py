from __future__ import annotations

from app.database import Base, SessionLocal, engine
from app.models.patient_case import PatientCase, PatientCaseConflict, PatientCaseVersion
from app.services.unified_patient_case_service import (
    get_patient_case,
    get_patient_case_history,
    get_patient_case_missing,
    get_patient_case_summary,
    resolve_case_for_decision,
    run_unified_patient_case_validation,
    upsert_from_free_text,
    upsert_from_generic_update,
    upsert_from_questionnaire,
)


def _cleanup(db: SessionLocal, case_id: int) -> None:
    db.query(PatientCaseConflict).filter(PatientCaseConflict.patient_case_id == case_id).delete()
    db.query(PatientCaseVersion).filter(PatientCaseVersion.patient_case_id == case_id).delete()
    db.query(PatientCase).filter(PatientCase.id == case_id).delete()
    db.commit()


def test_patient_case_merge_conflict_and_history() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    case_id = None
    try:
        created = upsert_from_free_text(
            db,
            case_text="My father is 84, uses a walker, moderate dementia, budget is $7,500 in Miami.",
            source_name="test",
        )
        case_id = int(created["id"])

        updated = upsert_from_free_text(
            db,
            patient_case_id=case_id,
            case_text="Update: budget is actually $12,000 and location is Tampa.",
            source_name="test",
        )

        assert updated["current_version"] >= 3
        assert int((updated.get("conflicts") or {}).get("open_conflicts") or 0) >= 1

        history = get_patient_case_history(db, case_id)
        assert history["id"] == case_id
        assert len(history["history"]) >= 3

        missing = get_patient_case_missing(db, case_id)
        assert isinstance(missing.get("follow_up_questions"), list)

        summary = get_patient_case_summary(db, case_id)
        assert "readiness" in summary
        assert "profile_confidence" in summary

        loaded = get_patient_case(db, case_id)
        assert loaded["id"] == case_id
    finally:
        if case_id is not None:
            _cleanup(db, case_id)
        db.close()


def test_patient_case_questionnaire_and_decision_resolution() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    case_id = None
    try:
        created = upsert_from_questionnaire(
            db,
            questionnaire_state={
                "relationship": "Dad",
                "ageGroup": "80-84",
                "assistanceLevel": "24/7 support required",
                "memoryStatus": "Mild memory issues",
                "budget": 7000,
                "distanceFromFamily": "Balanced location",
                "notes": "Needs PT, OT, medication support",
                "humanIntelligenceV2": {
                    "languageProfile": {"preferredSpokenLanguage": "English", "languagesUnderstood": ["English", "Spanish"]},
                    "transitionRiskProfile": {"postHospitalRehabNeed": "Yes"},
                },
            },
            source_name="test_questionnaire",
        )
        case_id = int(created["id"])

        resolved = resolve_case_for_decision(
            db,
            patient_case_id=case_id,
            questionnaire_state={},
            natural_language_query="",
            source_name="test_decision",
        )

        assert int(resolved["patient_case_id"]) == case_id
        handoff = resolved["questionnaire_state"]
        assert isinstance(handoff, dict)
        assert handoff.get("assistanceLevel")
    finally:
        if case_id is not None:
            _cleanup(db, case_id)
        db.close()


def test_unified_patient_case_validation_contract() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = run_unified_patient_case_validation(db)
        workload = result.get("workload") or {}
        outputs = result.get("results") or {}
        assert int(workload.get("questionnaire_sessions") or 0) >= 100
        assert int(workload.get("free_text_cases") or 0) >= 100
        assert int(workload.get("mixed_interactions") or 0) >= 100
        assert int(workload.get("conflict_scenarios") or 0) >= 50
        assert int(workload.get("profile_revisions") or 0) >= 50
        assert bool(outputs.get("recommendation_consumes_canonical_case")) is True
        assert bool(outputs.get("backward_compatibility_preserved")) is True
    finally:
        db.close()

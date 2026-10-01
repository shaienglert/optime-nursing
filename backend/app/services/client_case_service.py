from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.client_case import ClientCase, ClientCaseEvent, ClientFacilityJourney, ClientQuestionnaireVersion
from app.services.canonical_structured_profile import SCHEMA_VERSION, build_structured_profile


def create_client_case(db: Session, *, questionnaire_state: dict, contact_name: str | None = None, email: str | None = None, phone: str | None = None, terms_accepted: bool = False) -> ClientCase:
    structured = build_structured_profile(questionnaire_state)
    structured_json = json.dumps(structured, ensure_ascii=False)
    row = ClientCase(contact_name=contact_name, email=email, phone=phone, terms_accepted_at=datetime.now(timezone.utc) if terms_accepted else None, questionnaire_state_json=json.dumps(questionnaire_state, ensure_ascii=False), structured_profile_schema_version=SCHEMA_VERSION, structured_profile_version=1, structured_profile_json=structured_json)
    db.add(row); db.flush()
    db.add(ClientQuestionnaireVersion(case_id=row.id, version=1, questionnaire_state_json=row.questionnaire_state_json, structured_profile_schema_version=SCHEMA_VERSION, structured_profile_json=structured_json, change_summary="Initial saved questionnaire"))
    db.add(ClientCaseEvent(case_id=row.id, event_type="CASE_CREATED", payload_json="{}"))
    db.commit(); db.refresh(row)
    return row


def add_case_event(db: Session, case: ClientCase, *, event_type: str, facility_id: str | None = None, status: str | None = None, note: str | None = None, payload: dict | None = None, created_by: str | None = None) -> ClientCaseEvent:
    event = ClientCaseEvent(case_id=case.id, event_type=event_type, facility_id=facility_id, status=status, note=note, payload_json=json.dumps(payload or {}, ensure_ascii=False), created_by=created_by)
    db.add(event); db.commit(); db.refresh(event)
    return event


def set_facility_status(db: Session, case: ClientCase, facility_id: str, status: str, note: str | None = None) -> ClientFacilityJourney:
    journey = db.query(ClientFacilityJourney).filter_by(case_id=case.id, facility_id=facility_id).one_or_none()
    if journey is None:
        journey = ClientFacilityJourney(case_id=case.id, facility_id=facility_id)
        db.add(journey)
    journey.status = status
    journey.notes = note or journey.notes
    now = datetime.now(timezone.utc)
    if status == "REFERRED" and journey.referred_at is None: journey.referred_at = now
    if status == "TOUR_SCHEDULED": journey.tour_at = now
    if status == "SELECTED" and journey.selected_at is None: journey.selected_at = now
    if status == "MOVED_IN" and journey.move_in_at is None: journey.move_in_at = now
    db.flush()
    db.add(ClientCaseEvent(case_id=case.id, event_type="FACILITY_STATUS_CHANGED", facility_id=facility_id, status=status, note=note, payload_json="{}"))
    db.commit(); db.refresh(journey)
    return journey


def case_record(db: Session, token: str) -> dict | None:
    case = db.query(ClientCase).filter_by(case_token=token).one_or_none()
    if case is None: return None
    events = db.query(ClientCaseEvent).filter_by(case_id=case.id).order_by(ClientCaseEvent.created_at.desc()).all()
    facilities = db.query(ClientFacilityJourney).filter_by(case_id=case.id).order_by(ClientFacilityJourney.updated_at.desc()).all()
    return {
        "case_token": case.case_token, "status": case.status, "contact_name": case.contact_name, "email": case.email, "phone": case.phone,
        "terms_accepted_at": case.terms_accepted_at, "assigned_to": case.assigned_to, "next_follow_up_at": case.next_follow_up_at,
        "created_at": case.created_at, "updated_at": case.updated_at,
        "questionnaire_state": json.loads(case.questionnaire_state_json or "{}"),
        "structured_profile_schema_version": case.structured_profile_schema_version,
        "structured_profile_version": case.structured_profile_version,
        "structured_profile": json.loads(case.structured_profile_json or "{}"),
        "questionnaire_versions": [{"version": x.version, "change_summary": x.change_summary, "created_at": x.created_at} for x in db.query(ClientQuestionnaireVersion).filter_by(case_id=case.id).order_by(ClientQuestionnaireVersion.version.desc()).all()],
        "events": [{"event_type": x.event_type, "facility_id": x.facility_id, "status": x.status, "note": x.note, "created_by": x.created_by, "created_at": x.created_at} for x in events],
        "facilities": [{"facility_id": x.facility_id, "status": x.status, "referred_at": x.referred_at, "tour_at": x.tour_at, "selected_at": x.selected_at, "move_in_at": x.move_in_at, "sixty_day_status": x.sixty_day_status, "welcome_package_status": x.welcome_package_status, "fee_status": x.fee_status, "notes": x.notes} for x in facilities],
    }


def save_questionnaire_version(db: Session, case: ClientCase, questionnaire_state: dict, change_summary: str | None = None) -> ClientQuestionnaireVersion:
    latest = db.query(ClientQuestionnaireVersion).filter_by(case_id=case.id).order_by(ClientQuestionnaireVersion.version.desc()).first()
    version = (latest.version if latest else 0) + 1
    encoded = json.dumps(questionnaire_state, ensure_ascii=False)
    structured = build_structured_profile(questionnaire_state)
    structured_json = json.dumps(structured, ensure_ascii=False)
    row = ClientQuestionnaireVersion(case_id=case.id, version=version, questionnaire_state_json=encoded, structured_profile_schema_version=SCHEMA_VERSION, structured_profile_json=structured_json, change_summary=change_summary)
    case.questionnaire_state_json = encoded
    case.structured_profile_schema_version = SCHEMA_VERSION
    case.structured_profile_version = version
    case.structured_profile_json = structured_json
    db.add(row)
    db.add(ClientCaseEvent(case_id=case.id, event_type="QUESTIONNAIRE_UPDATED", note=change_summary, payload_json=json.dumps({"version": version})))
    db.commit(); db.refresh(row)
    return row

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


def _token() -> str:
    return uuid.uuid4().hex


class ClientCase(Base):
    __tablename__ = "client_cases"

    id = Column(Integer, primary_key=True)
    case_token = Column(String(32), nullable=False, unique=True, index=True, default=_token)
    status = Column(String(40), nullable=False, default="NEW", index=True)
    contact_name = Column(String(160), nullable=True)
    email = Column(String(320), nullable=True, index=True)
    phone = Column(String(80), nullable=True)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    questionnaire_state_json = Column(Text, nullable=False, default="{}")
    latest_decision_id = Column(String(80), nullable=True)
    assigned_to = Column(String(160), nullable=True)
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ClientQuestionnaireVersion(Base):
    __tablename__ = "client_questionnaire_versions"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("client_cases.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    questionnaire_state_json = Column(Text, nullable=False)
    change_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClientCaseEvent(Base):
    __tablename__ = "client_case_events"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("client_cases.id"), nullable=False, index=True)
    event_type = Column(String(60), nullable=False, index=True)
    facility_id = Column(String(100), nullable=True, index=True)
    status = Column(String(60), nullable=True)
    note = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False, default="{}")
    created_by = Column(String(160), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClientFacilityJourney(Base):
    __tablename__ = "client_facility_journeys"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("client_cases.id"), nullable=False, index=True)
    facility_id = Column(String(100), nullable=False, index=True)
    status = Column(String(60), nullable=False, default="SAVED")
    referred_at = Column(DateTime(timezone=True), nullable=True)
    tour_at = Column(DateTime(timezone=True), nullable=True)
    selected_at = Column(DateTime(timezone=True), nullable=True)
    move_in_at = Column(DateTime(timezone=True), nullable=True)
    sixty_day_status = Column(String(60), nullable=True)
    welcome_package_status = Column(String(60), nullable=True)
    fee_status = Column(String(60), nullable=True)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

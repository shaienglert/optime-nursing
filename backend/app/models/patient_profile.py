from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    __table_args__ = (
        UniqueConstraint("case_key", name="uq_patient_profiles_case_key"),
        Index("ix_patient_profiles_created", "created_at"),
        Index("ix_patient_profiles_updated", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    case_key = Column(String(80), nullable=False, index=True)
    original_case_text = Column(Text, nullable=False)
    latest_case_text = Column(Text, nullable=False)
    current_version = Column(Integer, nullable=False, default=1)
    profile_confidence = Column(Float, nullable=False, default=0.0)
    structured_profile_json = Column(Text, nullable=False, default="{}")
    missing_fields_json = Column(Text, nullable=False, default="[]")
    follow_up_questions_json = Column(Text, nullable=False, default="[]")
    ambiguity_notes_json = Column(Text, nullable=False, default="[]")
    case_summary = Column(Text, nullable=False, default="")
    questionnaire_state_json = Column(Text, nullable=False, default="{}")
    decision_handoff_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    versions = relationship("PatientProfileVersion", back_populates="profile", cascade="all, delete-orphan")


class PatientProfileVersion(Base):
    __tablename__ = "patient_profile_versions"
    __table_args__ = (
        UniqueConstraint("profile_id", "version_number", name="uq_patient_profile_versions_profile_version"),
        Index("ix_patient_profile_versions_profile", "profile_id", "version_number"),
        Index("ix_patient_profile_versions_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("patient_profiles.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    operation = Column(String(32), nullable=False)
    input_case_text = Column(Text, nullable=False)
    profile_confidence = Column(Float, nullable=False, default=0.0)
    structured_profile_json = Column(Text, nullable=False, default="{}")
    missing_fields_json = Column(Text, nullable=False, default="[]")
    follow_up_questions_json = Column(Text, nullable=False, default="[]")
    ambiguity_notes_json = Column(Text, nullable=False, default="[]")
    case_summary = Column(Text, nullable=False, default="")
    questionnaire_state_json = Column(Text, nullable=False, default="{}")
    decision_handoff_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profile = relationship("PatientProfile", back_populates="versions")

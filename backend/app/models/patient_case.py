from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PatientCase(Base):
    __tablename__ = "patient_cases"
    __table_args__ = (
        UniqueConstraint("case_key", name="uq_patient_cases_case_key"),
        Index("ix_patient_cases_created", "created_at"),
        Index("ix_patient_cases_updated", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    case_key = Column(String(80), nullable=False, index=True)
    display_label = Column(String(200), nullable=False, default="")
    current_version = Column(Integer, nullable=False, default=1)
    profile_confidence = Column(Float, nullable=False, default=0.0)
    canonical_profile_json = Column(Text, nullable=False, default="{}")
    questionnaire_state_json = Column(Text, nullable=False, default="{}")
    natural_language_summary = Column(Text, nullable=False, default="")
    readiness_json = Column(Text, nullable=False, default="{}")
    missing_critical_json = Column(Text, nullable=False, default="[]")
    follow_up_questions_json = Column(Text, nullable=False, default="[]")
    conflict_summary_json = Column(Text, nullable=False, default="{}")
    source_matrix_json = Column(Text, nullable=False, default="{}")
    latest_decision_handoff_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    versions = relationship("PatientCaseVersion", back_populates="patient_case", cascade="all, delete-orphan")
    conflicts = relationship("PatientCaseConflict", back_populates="patient_case", cascade="all, delete-orphan")


class PatientCaseVersion(Base):
    __tablename__ = "patient_case_versions"
    __table_args__ = (
        UniqueConstraint("patient_case_id", "version_number", name="uq_patient_case_versions_case_version"),
        Index("ix_patient_case_versions_case", "patient_case_id", "version_number"),
        Index("ix_patient_case_versions_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_case_id = Column(Integer, ForeignKey("patient_cases.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    source_type = Column(String(40), nullable=False)
    source_name = Column(String(120), nullable=False, default="")
    reason = Column(String(200), nullable=False, default="")
    changed_fields_json = Column(Text, nullable=False, default="[]")
    previous_values_json = Column(Text, nullable=False, default="{}")
    new_values_json = Column(Text, nullable=False, default="{}")
    canonical_profile_json = Column(Text, nullable=False, default="{}")
    questionnaire_state_json = Column(Text, nullable=False, default="{}")
    readiness_json = Column(Text, nullable=False, default="{}")
    missing_critical_json = Column(Text, nullable=False, default="[]")
    latest_decision_handoff_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient_case = relationship("PatientCase", back_populates="versions")


class PatientCaseConflict(Base):
    __tablename__ = "patient_case_conflicts"
    __table_args__ = (
        Index("ix_patient_case_conflicts_case", "patient_case_id", "created_at"),
        Index("ix_patient_case_conflicts_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_case_id = Column(Integer, ForeignKey("patient_cases.id"), nullable=False, index=True)
    field_path = Column(String(200), nullable=False, index=True)
    conflict_type = Column(String(40), nullable=False)
    existing_value_json = Column(Text, nullable=False, default="null")
    new_value_json = Column(Text, nullable=False, default="null")
    existing_confidence = Column(Float, nullable=False, default=0.0)
    new_confidence = Column(Float, nullable=False, default=0.0)
    resolution = Column(String(40), nullable=False, default="PENDING")
    resolution_reason = Column(Text, nullable=False, default="")
    status = Column(String(24), nullable=False, default="OPEN")
    source_type = Column(String(40), nullable=False, default="UNKNOWN")
    source_name = Column(String(120), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient_case = relationship("PatientCase", back_populates="conflicts")

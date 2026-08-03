from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class FacilityEvidenceRegistry(Base):
    __tablename__ = "facility_evidence_registry"
    __table_args__ = (
        UniqueConstraint("evidence_id", name="uq_facility_evidence_registry_evidence_id"),
        Index("ix_facility_evidence_registry_facility_parameter", "facility_id", "parameter_id"),
        Index("ix_facility_evidence_registry_source", "source_type", "source"),
        Index("ix_facility_evidence_registry_verification", "verification_status", "preferred"),
        Index("ix_facility_evidence_registry_conflict", "conflict_status"),
        Index("ix_facility_evidence_registry_dedup", "dedup_group_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String(120), nullable=False, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=True, index=True)
    parameter_id = Column(String(120), nullable=False, index=True)
    parameter_name = Column(String(255), nullable=False)
    parameter_value = Column(Text, nullable=True)
    source = Column(String(160), nullable=False)
    source_type = Column(String(80), nullable=False)
    source_url = Column(Text, nullable=True)
    collection_method = Column(String(120), nullable=False)
    collected_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_status = Column(String(40), nullable=False, default="UNKNOWN")
    confidence_score = Column(Float, nullable=False, default=0.0)
    importance_score = Column(Float, nullable=False, default=0.0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    runtime_version = Column(String(80), nullable=True)
    connector = Column(String(80), nullable=False)
    conflict_status = Column(String(40), nullable=False, default="NO_CONFLICT")
    preferred = Column(Boolean, nullable=False, default=False)
    affects_recommendation = Column(Boolean, nullable=False, default=False)
    dedup_group_key = Column(String(120), nullable=False, default="")
    merged_from_json = Column(Text, nullable=False, default="[]")
    source_history_json = Column(Text, nullable=False, default="[]")
    raw_payload_json = Column(Text, nullable=False, default="{}")
    current_version = Column(Integer, nullable=False, default=1)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    versions = relationship("FacilityEvidenceRegistryVersion", back_populates="evidence", cascade="all, delete-orphan")


class FacilityEvidenceRegistryVersion(Base):
    __tablename__ = "facility_evidence_registry_versions"
    __table_args__ = (
        UniqueConstraint("evidence_id", "version_number", name="uq_facility_evidence_registry_versions_evidence_version"),
        Index("ix_facility_evidence_registry_versions_evidence", "evidence_id", "version_number"),
        Index("ix_facility_evidence_registry_versions_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String(120), ForeignKey("facility_evidence_registry.evidence_id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    action = Column(String(40), nullable=False)
    snapshot_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evidence = relationship("FacilityEvidenceRegistry", back_populates="versions")

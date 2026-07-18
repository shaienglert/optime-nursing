from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.sql import func

from app.database import Base


class KnowledgeObject(Base):
    __tablename__ = "knowledge_objects"
    __table_args__ = (
        UniqueConstraint("object_key", name="uq_knowledge_objects_object_key"),
        Index("ix_knowledge_objects_entity_type", "entity_type", "entity_key"),
        Index("ix_knowledge_objects_owner_status", "owner_agent", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    object_key = Column(String(160), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="")
    category = Column(String(120), nullable=False, default="GENERAL")
    topic = Column(String(160), nullable=False)
    entity_type = Column(String(80), nullable=False)
    entity_key = Column(String(160), nullable=False)
    relationship = Column(String(120), nullable=True)
    property_name = Column(String(160), nullable=False, default="fact")
    fact_value = Column(Text, nullable=False)
    source_name = Column(String(160), nullable=False, default="UNKNOWN")
    source_type = Column(String(80), nullable=False, default="UNKNOWN")
    source_reference = Column(Text, nullable=True)
    trust_level = Column(String(32), nullable=False, default="LEVEL_D")
    evidence_key = Column(String(160), nullable=True)
    evidence_summary = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=True)
    verification_status = Column(String(32), nullable=False, default="UNVERIFIED")
    verification_type = Column(String(64), nullable=False, default="PENDING_VERIFICATION")
    freshness_status = Column(String(32), nullable=False, default="FRESH")
    confidence = Column(Float, nullable=False, default=0.0)
    owner_agent = Column(String(80), nullable=False)
    verified_by = Column(String(120), nullable=True)
    reviewer = Column(String(120), nullable=True)
    recommendation_eligible = Column(Integer, nullable=False, default=0)
    conflict_status = Column(String(32), nullable=False, default="NO_CONFLICT")
    status = Column(String(32), nullable=False, default="ACTIVE")
    source_diversity = Column(Integer, nullable=False, default=1)
    completeness = Column(Float, nullable=False, default=0.0)
    consistency = Column(Float, nullable=False, default=0.0)
    evidence_strength = Column(String(32), nullable=False, default="MODERATE")
    version = Column(String(40), nullable=False, default="v1")
    audit_history_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    next_review_at = Column(DateTime(timezone=True), nullable=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)


class KnowledgeEvidence(Base):
    __tablename__ = "knowledge_evidence"
    __table_args__ = (
        UniqueConstraint("evidence_key", name="uq_knowledge_evidence_evidence_key"),
        Index("ix_knowledge_evidence_source_date", "source_name", "captured_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    evidence_key = Column(String(160), nullable=False, index=True)
    source_name = Column(String(160), nullable=False)
    source_url = Column(Text, nullable=True)
    source_type = Column(String(80), nullable=False, default="PUBLIC")
    trust_level = Column(String(32), nullable=False, default="MEDIUM")
    evidence_version = Column(String(40), nullable=False, default="v1")
    extracted_fact = Column(Text, nullable=False)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    raw_trace_reference = Column(Text, nullable=True)


class KnowledgeRelationship(Base):
    __tablename__ = "knowledge_relationships"
    __table_args__ = (
        UniqueConstraint("from_object_key", "relation", "to_object_key", name="uq_knowledge_relationships_triplet"),
        Index("ix_knowledge_relationships_relation", "relation"),
    )

    id = Column(Integer, primary_key=True, index=True)
    from_object_key = Column(String(160), ForeignKey("knowledge_objects.object_key"), nullable=False, index=True)
    relation = Column(String(120), nullable=False)
    to_object_key = Column(String(160), ForeignKey("knowledge_objects.object_key"), nullable=False, index=True)
    evidence_key = Column(String(160), ForeignKey("knowledge_evidence.evidence_key"), nullable=True, index=True)
    confidence = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class KnowledgeObjectHistory(Base):
    __tablename__ = "knowledge_object_history"
    __table_args__ = (
        Index("ix_knowledge_object_history_object_time", "object_key", "changed_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    object_key = Column(String(160), nullable=False, index=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_reason = Column(Text, nullable=False)
    evidence_version = Column(String(40), nullable=False, default="v1")
    verification_version = Column(String(40), nullable=False, default="v1")
    changed_by_agent = Column(String(80), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KnowledgeGovernanceRecord(Base):
    __tablename__ = "knowledge_governance_records"
    __table_args__ = (
        UniqueConstraint("object_key", name="uq_knowledge_governance_records_object_key"),
        Index("ix_knowledge_governance_records_review", "next_review_at", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    object_key = Column(String(160), nullable=False, index=True)
    owner_agent = Column(String(80), nullable=False)
    reviewer = Column(String(120), nullable=True)
    verification_date = Column(DateTime(timezone=True), nullable=True)
    review_frequency_days = Column(Integer, nullable=False, default=30)
    retirement_policy = Column(Text, nullable=True)
    audit_trail_reference = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="ACTIVE")
    next_review_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RecommendationVerificationAudit(Base):
    __tablename__ = "recommendation_verification_audits"
    __table_args__ = (
        Index("ix_recommendation_verification_audits_recommendation", "recommendation_key", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    recommendation_key = Column(String(160), nullable=False, index=True)
    resident_key = Column(String(160), nullable=True, index=True)
    facts_used_json = Column(Text, nullable=False, default="[]")
    knowledge_object_ids_json = Column(Text, nullable=False, default="[]")
    evidence_references_json = Column(Text, nullable=False, default="[]")
    decision_rules_applied_json = Column(Text, nullable=False, default="[]")
    professional_judgment_json = Column(Text, nullable=False, default="[]")
    model_version = Column(String(80), nullable=False, default="unknown")
    reviewer = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
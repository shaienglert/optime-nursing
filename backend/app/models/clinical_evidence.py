from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ClinicalTopic(Base):
    __tablename__ = "clinical_topics"

    id = Column(Integer, primary_key=True, index=True)
    topic_key = Column(String(120), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    audience = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    conditions = relationship("ClinicalCondition", back_populates="topic", cascade="all, delete-orphan")


class ClinicalCondition(Base):
    __tablename__ = "clinical_conditions"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("clinical_topics.id"), index=True, nullable=False)
    condition_key = Column(String(120), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    clinical_summary = Column(Text, nullable=True)
    family_language_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    topic = relationship("ClinicalTopic", back_populates="conditions")
    interventions = relationship("ClinicalIntervention", back_populates="condition", cascade="all, delete-orphan")


class ClinicalIntervention(Base):
    __tablename__ = "clinical_interventions"

    id = Column(Integer, primary_key=True, index=True)
    condition_id = Column(Integer, ForeignKey("clinical_conditions.id"), index=True, nullable=False)
    intervention_key = Column(String(120), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    rationale = Column(Text, nullable=True)
    family_language_rationale = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    condition = relationship("ClinicalCondition", back_populates="interventions")
    outcomes = relationship("ClinicalOutcome", back_populates="intervention", cascade="all, delete-orphan")


class ClinicalOutcome(Base):
    __tablename__ = "clinical_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(Integer, ForeignKey("clinical_interventions.id"), index=True, nullable=False)
    outcome_key = Column(String(120), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    quality_of_life_impact = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    intervention = relationship("ClinicalIntervention", back_populates="outcomes")


class ClinicalEvidence(Base):
    __tablename__ = "clinical_evidence"

    id = Column(Integer, primary_key=True, index=True)
    evidence_key = Column(String(120), unique=True, index=True, nullable=False)
    topic_key = Column(String(120), nullable=False)
    condition_key = Column(String(120), nullable=False)
    intervention_key = Column(String(120), nullable=False)
    outcome_key = Column(String(120), nullable=True)
    source = Column(String(120), nullable=False)
    publication_date = Column(Date, nullable=True)
    evidence_strength = Column(String(32), nullable=False)  # High, Moderate, Limited
    review_date = Column(Date, nullable=True)
    url = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClinicalGuideline(Base):
    __tablename__ = "clinical_guidelines"

    id = Column(Integer, primary_key=True, index=True)
    guideline_key = Column(String(120), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    source = Column(String(120), nullable=False)
    publication_date = Column(Date, nullable=True)
    review_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="ACTIVE")
    scope = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ClinicalReference(Base):
    __tablename__ = "clinical_references"

    id = Column(Integer, primary_key=True, index=True)
    reference_key = Column(String(120), unique=True, index=True, nullable=False)
    citation = Column(Text, nullable=False)
    source = Column(String(120), nullable=False)
    publication_date = Column(Date, nullable=True)
    url = Column(Text, nullable=True)
    evidence_strength = Column(String(32), nullable=False)
    review_date = Column(Date, nullable=True)
    abstract_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClinicalGraphEdge(Base):
    __tablename__ = "clinical_graph_edges"

    id = Column(Integer, primary_key=True, index=True)
    from_node = Column(String(160), nullable=False, index=True)
    relation = Column(String(80), nullable=False)
    to_node = Column(String(160), nullable=False, index=True)
    source_evidence_key = Column(String(120), nullable=False)
    evidence_strength = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RecommendationEvidenceLink(Base):
    __tablename__ = "recommendation_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_run_id = Column(String(120), index=True, nullable=False)
    facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
    statement = Column(Text, nullable=False)
    evidence_key = Column(String(120), nullable=False)
    evidence_confidence = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class SupplierVerificationRun(Base):
    __tablename__ = "supplier_verification_runs"
    __table_args__ = (Index("ix_supplier_verification_runs_completed", "completed_at"),)

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(80), nullable=False, default="oomnik-supplier-verification-agent")
    status = Column(String(24), nullable=False, default="RUNNING")
    records_processed = Column(Integer, nullable=False, default=0)
    source_requests = Column(Integer, nullable=False, default=0)
    reachable_sources = Column(Integer, nullable=False, default=0)
    stage_counts_json = Column(Text, nullable=False, default="{}")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class SupplierVerificationObservation(Base):
    __tablename__ = "supplier_verification_observations"
    __table_args__ = (
        UniqueConstraint("supplier_id", "source_url", "content_hash", name="uq_supplier_source_content"),
        Index("ix_supplier_verification_supplier_checked", "supplier_id", "checked_at"),
        Index("ix_supplier_verification_stage", "stage"),
    )

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, nullable=True, index=True)
    supplier_id = Column(String(120), nullable=False, index=True)
    supplier_name = Column(String(255), nullable=False)
    stage = Column(String(60), nullable=False)
    source_url = Column(Text, nullable=False)
    source_kind = Column(String(40), nullable=False)
    http_status = Column(Integer, nullable=True)
    reachable = Column(Integer, nullable=False, default=0)
    identity_match = Column(Integer, nullable=False, default=0)
    market_match = Column(Integer, nullable=False, default=0)
    credential_observed = Column(Integer, nullable=False, default=0)
    content_hash = Column(String(64), nullable=False)
    evidence_json = Column(Text, nullable=False, default="{}")
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

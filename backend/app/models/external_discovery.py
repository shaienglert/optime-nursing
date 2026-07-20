from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class ExternalSourceConnectorHealth(Base):
    __tablename__ = "external_source_connector_health"
    __table_args__ = (
        UniqueConstraint("source_key", name="uq_external_source_connector_health_source_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_key = Column(String(255), nullable=False, index=True)
    source_name = Column(String(160), nullable=False)
    source_type = Column(String(80), nullable=False)
    source_locator = Column(Text, nullable=False)
    facilities_covered = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    last_new_value_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_reason = Column(Text, nullable=True)
    next_refresh_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ExternalSourceRequestLog(Base):
    __tablename__ = "external_source_request_logs"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "facility_id",
            "source_locator",
            "claim_type",
            "claim_value",
            name="uq_external_source_request_log_request",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(80), nullable=False, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    facility_id = Column(Integer, nullable=False, index=True)
    facility_cms_id = Column(String(20), nullable=False, index=True)
    facility_name = Column(String(255), nullable=False)
    source_name = Column(String(160), nullable=False)
    source_type = Column(String(80), nullable=False)
    source_locator = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    request_status = Column(String(40), nullable=False)
    change_status = Column(String(40), nullable=False, default="UNKNOWN")
    claim_type = Column(String(80), nullable=False)
    claim_value = Column(Text, nullable=False)
    previous_value = Column(Text, nullable=True)
    verification_status = Column(String(40), nullable=False, default="UNVERIFIED")
    published_at = Column(DateTime(timezone=True), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    evidence_key = Column(String(255), nullable=True)
    knowledge_object_key = Column(String(255), nullable=True)
    response_code = Column(Integer, nullable=True)
    failure_reason = Column(Text, nullable=True)
    raw_text_snippet = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
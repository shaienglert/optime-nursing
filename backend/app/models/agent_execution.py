from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.sql import func

from app.database import Base


class AgentWorker(Base):
    __tablename__ = "agent_workers"
    __table_args__ = (
        UniqueConstraint("agent_key", name="uq_agent_workers_agent_key"),
        Index("ix_agent_workers_status_next_run", "status", "next_run"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    mission = Column(Text, nullable=False)
    data_sources = Column(Text, nullable=False, default="[]")
    queue_type = Column(String(80), nullable=False)
    status = Column(String(24), nullable=False, default="IDLE")
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)
    runtime_ms = Column(Integer, nullable=False, default=0)
    items_processed = Column(Integer, nullable=False, default=0)
    items_added = Column(Integer, nullable=False, default=0)
    items_updated = Column(Integer, nullable=False, default=0)
    errors = Column(Integer, nullable=False, default=0)
    confidence_change = Column(Float, nullable=False, default=0.0)
    knowledge_records = Column(Integer, nullable=False, default=0)
    coverage = Column(Float, nullable=False, default=0.0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AgentDependency(Base):
    __tablename__ = "agent_dependencies"
    __table_args__ = (
        UniqueConstraint("agent_key", "depends_on_agent_key", name="uq_agent_dependencies"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    depends_on_agent_key = Column(String(80), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentQueueItem(Base):
    __tablename__ = "agent_queue_items"
    __table_args__ = (
        Index("ix_agent_queue_items_type_status", "queue_type", "status"),
        Index("ix_agent_queue_items_available", "available_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    queue_type = Column(String(80), nullable=False)
    agent_key = Column(String(80), nullable=True, index=True)
    payload_json = Column(Text, nullable=False, default="{}")
    status = Column(String(24), nullable=False, default="PENDING")
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    available_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentJobRun(Base):
    __tablename__ = "agent_job_runs"
    __table_args__ = (
        Index("ix_agent_job_runs_agent_started", "agent_key", "started_at"),
        Index("ix_agent_job_runs_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(24), nullable=False, default="RUNNING")
    runtime_ms = Column(Integer, nullable=False, default=0)
    items_processed = Column(Integer, nullable=False, default=0)
    items_added = Column(Integer, nullable=False, default=0)
    items_updated = Column(Integer, nullable=False, default=0)
    errors = Column(Integer, nullable=False, default=0)
    confidence_change = Column(Float, nullable=False, default=0.0)
    knowledge_gained_json = Column(Text, nullable=False, default="{}")


class AgentKnowledgeRecord(Base):
    __tablename__ = "agent_knowledge_records"
    __table_args__ = (
        Index("ix_agent_knowledge_records_agent_type", "agent_key", "record_type"),
        Index("ix_agent_knowledge_records_entity", "entity_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    record_type = Column(String(80), nullable=False)
    entity_key = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=False, default="{}")
    confidence = Column(Float, nullable=False, default=0.0)
    source = Column(String(120), nullable=False, default="SYSTEM")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentMetricSnapshot(Base):
    __tablename__ = "agent_metric_snapshots"
    __table_args__ = (
        Index("ix_agent_metric_snapshots_agent_ts", "agent_key", "captured_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(24), nullable=False)
    runtime_ms = Column(Integer, nullable=False, default=0)
    items_processed = Column(Integer, nullable=False, default=0)
    items_added = Column(Integer, nullable=False, default=0)
    items_updated = Column(Integer, nullable=False, default=0)
    errors = Column(Integer, nullable=False, default=0)
    confidence_change = Column(Float, nullable=False, default=0.0)
    coverage = Column(Float, nullable=False, default=0.0)


class AgentVersionSnapshot(Base):
    __tablename__ = "agent_version_snapshots"
    __table_args__ = (
        UniqueConstraint("agent_key", name="uq_agent_version_snapshots_agent_key"),
        Index("ix_agent_version_snapshots_updated", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    agent_name = Column(String(120), nullable=False)
    domain = Column(String(120), nullable=False)
    agent_version = Column(String(40), nullable=False)
    knowledge_version = Column(String(40), nullable=False)
    model_version = Column(String(80), nullable=False)
    prompt_version = Column(String(80), nullable=True)
    evidence_version = Column(String(40), nullable=False)
    schema_version = Column(String(40), nullable=False)
    api_version = Column(String(40), nullable=False)
    health_status = Column(String(24), nullable=False, default="HEALTHY")
    average_confidence = Column(Float, nullable=False, default=0.0)
    last_learning_date = Column(DateTime(timezone=True), nullable=True)
    next_scheduled_update = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RecommendationAgentVersionTrace(Base):
    __tablename__ = "recommendation_agent_version_traces"
    __table_args__ = (
        Index("ix_recommendation_agent_version_traces_key", "recommendation_key"),
        Index("ix_recommendation_agent_version_traces_agent", "agent_key"),
        UniqueConstraint("recommendation_key", "agent_key", name="uq_recommendation_agent_version_trace"),
    )

    id = Column(Integer, primary_key=True, index=True)
    recommendation_key = Column(String(120), nullable=False, index=True)
    resident_key = Column(String(120), nullable=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    agent_version = Column(String(40), nullable=False)
    knowledge_version = Column(String(40), nullable=False)
    model_version = Column(String(80), nullable=False)
    prompt_version = Column(String(80), nullable=True)
    evidence_version = Column(String(40), nullable=False)
    schema_version = Column(String(40), nullable=False)
    api_version = Column(String(40), nullable=False)
    contribution_scope = Column(String(120), nullable=False, default="knowledge")
    contribution_summary = Column(Text, nullable=False, default="")
    contributed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentKnowledgeReportSnapshot(Base):
    __tablename__ = "agent_knowledge_report_snapshots"
    __table_args__ = (
        UniqueConstraint("agent_key", name="uq_agent_knowledge_report_snapshots_agent_key"),
        Index("ix_agent_knowledge_report_snapshots_next_refresh", "next_refresh_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    agent_name = Column(String(120), nullable=False)
    domain = Column(String(120), nullable=False)
    report_json = Column(Text, nullable=False, default="{}")
    knowledge_count = Column(Integer, nullable=False, default=0)
    evidence_count = Column(Integer, nullable=False, default=0)
    coverage = Column(Float, nullable=False, default=0.0)
    average_confidence = Column(Float, nullable=False, default=0.0)
    health_status = Column(String(24), nullable=False, default="HEALTHY")
    freshness_status = Column(String(24), nullable=False, default="FRESH")
    knowledge_age_seconds = Column(Integer, nullable=False, default=0)
    last_successful_refresh = Column(DateTime(timezone=True), nullable=True)
    last_refresh_attempt = Column(DateTime(timezone=True), nullable=True)
    refresh_duration_ms = Column(Integer, nullable=False, default=0)
    verified_until = Column(DateTime(timezone=True), nullable=True)
    ttl_seconds = Column(Integer, nullable=False, default=3600)
    pending_changes = Column(Integer, nullable=False, default=0)
    pending_reviews = Column(Integer, nullable=False, default=0)
    failed_refresh_count = Column(Integer, nullable=False, default=0)
    last_refreshed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    next_refresh_at = Column(DateTime(timezone=True), nullable=True)
    refresh_status = Column(String(24), nullable=False, default="READY")
    refresh_error = Column(Text, nullable=True)


class AgentKnowledgeRefreshEvent(Base):
    __tablename__ = "agent_knowledge_refresh_events"
    __table_args__ = (
        Index("ix_agent_knowledge_refresh_events_agent_time", "agent_key", "started_at"),
        Index("ix_agent_knowledge_refresh_events_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    refresh_mode = Column(String(32), nullable=False, default="scheduled")
    status = Column(String(24), nullable=False, default="SUCCESS")
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)


class RecommendationKnowledgeUsageLog(Base):
    __tablename__ = "recommendation_knowledge_usage_logs"
    __table_args__ = (
        Index("ix_recommendation_knowledge_usage_logs_rec", "recommendation_key"),
        Index("ix_recommendation_knowledge_usage_logs_agent", "agent_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    recommendation_key = Column(String(120), nullable=False, index=True)
    resident_key = Column(String(120), nullable=True, index=True)
    agent_key = Column(String(80), nullable=False, index=True)
    freshness_status = Column(String(24), nullable=False)
    health_status = Column(String(24), nullable=False)
    verification_status = Column(String(24), nullable=False, default="VERIFIED")
    confidence = Column(Float, nullable=False, default=0.0)
    used_stale = Column(Integer, nullable=False, default=0)
    policy_allowed = Column(Integer, nullable=False, default=1)
    decision = Column(String(24), nullable=False, default="USED")
    decision_reason = Column(Text, nullable=False, default="")
    logged_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupervisorIncidentLog(Base):
    __tablename__ = "supervisor_incident_logs"
    __table_args__ = (
        Index("ix_supervisor_incident_logs_created", "created_at"),
        Index("ix_supervisor_incident_logs_agent", "agent_key"),
        Index("ix_supervisor_incident_logs_severity", "severity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    incident_type = Column(String(64), nullable=False)
    severity = Column(String(24), nullable=False, default="MEDIUM")
    status = Column(String(24), nullable=False, default="OPEN")
    agent_key = Column(String(80), nullable=True, index=True)
    domain = Column(String(120), nullable=True)
    summary = Column(Text, nullable=False)
    details_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

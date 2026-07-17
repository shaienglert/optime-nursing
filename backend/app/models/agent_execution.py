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

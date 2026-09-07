from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _column_names(engine: Engine, table_name: str) -> set[str]:
    inspector = inspect(engine)
    try:
        return {column["name"] for column in inspector.get_columns(table_name)}
    except Exception:
        return set()


def ensure_provider_identity_schema(engine: Engine) -> None:
    columns = _column_names(engine, "facility_users")
    if not columns:
        return

    alter_statements: list[str] = []

    if "is_verified" not in columns:
        alter_statements.append("ALTER TABLE facility_users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0")
    if "verification_sent_at" not in columns:
        alter_statements.append("ALTER TABLE facility_users ADD COLUMN verification_sent_at DATETIME NULL")
    if "verification_completed_at" not in columns:
        alter_statements.append("ALTER TABLE facility_users ADD COLUMN verification_completed_at DATETIME NULL")
    if "verification_method" not in columns:
        alter_statements.append("ALTER TABLE facility_users ADD COLUMN verification_method VARCHAR(40) NULL")
    if "verified_badge" not in columns:
        alter_statements.append("ALTER TABLE facility_users ADD COLUMN verified_badge BOOLEAN NOT NULL DEFAULT 0")
    if "next_reverification_due_at" not in columns:
        alter_statements.append("ALTER TABLE facility_users ADD COLUMN next_reverification_due_at DATETIME NULL")

    if not alter_statements:
        return

    with engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))


def ensure_facility_intelligence_profile_schema(engine: Engine) -> None:
    columns = _column_names(engine, "facility_intelligence_profiles")
    if not columns:
        return

    alter_statements: list[str] = []

    if "signal_details" not in columns:
        alter_statements.append("ALTER TABLE facility_intelligence_profiles ADD COLUMN signal_details TEXT NOT NULL DEFAULT '[]'")
    if "visual_hero_image" not in columns:
        alter_statements.append("ALTER TABLE facility_intelligence_profiles ADD COLUMN visual_hero_image TEXT NOT NULL DEFAULT '{}' ")
    if "visual_gallery_images" not in columns:
        alter_statements.append("ALTER TABLE facility_intelligence_profiles ADD COLUMN visual_gallery_images TEXT NOT NULL DEFAULT '[]'")
    if "visual_lifestyle_tags" not in columns:
        alter_statements.append("ALTER TABLE facility_intelligence_profiles ADD COLUMN visual_lifestyle_tags TEXT NOT NULL DEFAULT '[]'")
    if "visual_confidence_score" not in columns:
        alter_statements.append("ALTER TABLE facility_intelligence_profiles ADD COLUMN visual_confidence_score FLOAT NOT NULL DEFAULT 0.0")
    if "visual_coverage_score" not in columns:
        alter_statements.append("ALTER TABLE facility_intelligence_profiles ADD COLUMN visual_coverage_score FLOAT NOT NULL DEFAULT 0.0")

    if not alter_statements:
        return

    with engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))


def ensure_agent_knowledge_report_snapshot_schema(engine: Engine) -> None:
    columns = _column_names(engine, "agent_knowledge_report_snapshots")
    if not columns:
        return

    alter_statements: list[str] = []

    if "freshness_status" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN freshness_status VARCHAR(24) NOT NULL DEFAULT 'FRESH'")
    if "knowledge_age_seconds" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN knowledge_age_seconds INTEGER NOT NULL DEFAULT 0")
    if "last_successful_refresh" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN last_successful_refresh DATETIME NULL")
    if "last_refresh_attempt" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN last_refresh_attempt DATETIME NULL")
    if "refresh_duration_ms" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN refresh_duration_ms INTEGER NOT NULL DEFAULT 0")
    if "verified_until" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN verified_until DATETIME NULL")
    if "ttl_seconds" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN ttl_seconds INTEGER NOT NULL DEFAULT 3600")
    if "pending_changes" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN pending_changes INTEGER NOT NULL DEFAULT 0")
    if "pending_reviews" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN pending_reviews INTEGER NOT NULL DEFAULT 0")
    if "failed_refresh_count" not in columns:
        alter_statements.append("ALTER TABLE agent_knowledge_report_snapshots ADD COLUMN failed_refresh_count INTEGER NOT NULL DEFAULT 0")

    if not alter_statements:
        return

    with engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))


def ensure_state_license_schema(engine: Engine) -> None:
    """Nevada and other state licences on facility_license_records.

    A community that is not Medicare-certified has no CCN, so its state credential is the
    only public identity it carries. Existing databases predate these columns; the model
    alone would only serve a freshly created schema.
    """
    columns = _column_names(engine, "facility_license_records")
    if not columns:
        return

    alter_statements: list[str] = []

    if "state_license_number" not in columns:
        alter_statements.append("ALTER TABLE facility_license_records ADD COLUMN state_license_number VARCHAR(40) NULL")
    if "state_license_type" not in columns:
        alter_statements.append("ALTER TABLE facility_license_records ADD COLUMN state_license_type VARCHAR(20) NULL")
    if "state_care_type" not in columns:
        alter_statements.append("ALTER TABLE facility_license_records ADD COLUMN state_care_type VARCHAR(60) NULL")
    if "state_endorsements" not in columns:
        alter_statements.append("ALTER TABLE facility_license_records ADD COLUMN state_endorsements TEXT NULL")
    if "state_source_url" not in columns:
        alter_statements.append("ALTER TABLE facility_license_records ADD COLUMN state_source_url VARCHAR(500) NULL")

    if not alter_statements:
        return

    with engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))

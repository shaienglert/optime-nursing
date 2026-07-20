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

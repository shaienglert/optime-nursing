from contextlib import contextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import postgresql

from app.services import schema_migrations as migrations


MIGRATIONS = [
    (migrations.ensure_provider_identity_schema, "facility_users", "verification_sent_at"),
    (migrations.ensure_agent_knowledge_report_snapshot_schema, "agent_knowledge_report_snapshots", "last_successful_refresh"),
    (migrations.ensure_facility_room_pricing_schema, "facility_room_types", "observed_at"),
]


@pytest.mark.parametrize("migrate,table,date_column", MIGRATIONS)
def test_postgres_existing_schema_uses_native_timestamp(migrate, table, date_column):
    statements = []

    class RecordingEngine:
        dialect = postgresql.dialect()

        @contextmanager
        def begin(self):
            yield self

        def execute(self, statement):
            statements.append(str(statement))

    with patch.object(migrations, "_column_names", return_value={"id"}):
        migrate(RecordingEngine())
    assert any(f"{date_column} TIMESTAMP WITHOUT TIME ZONE NULL" in sql for sql in statements)
    assert all("DATETIME" not in sql for sql in statements)
    boolean_statements = [sql for sql in statements if "BOOLEAN" in sql]
    assert all("DEFAULT FALSE" in sql for sql in boolean_statements)
    if table == "facility_users":
        assert len(boolean_statements) == 2


@pytest.mark.parametrize("migrate,table,date_column", MIGRATIONS)
def test_existing_sqlite_rows_survive_repeated_migration(migrate, table, date_column):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
        connection.execute(text(f"INSERT INTO {table} (id) VALUES (1)"))
    migrate(engine)
    migrate(engine)
    assert date_column in {column["name"] for column in inspect(engine).get_columns(table)}
    with engine.connect() as connection:
        assert connection.execute(text(f"SELECT id, {date_column} FROM {table}")).all() == [(1, None)]
        if table == "facility_users":
            assert connection.execute(text(f"SELECT is_verified, verified_badge FROM {table}")).one() == (0, 0)

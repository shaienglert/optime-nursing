from sqlalchemy import create_engine, text
from app.database import Base
import app.models.client_case
from app.services.schema_migrations import ensure_client_structured_profile_schema

def test_structured_profile_schema_migration_is_idempotent():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_client_structured_profile_schema(engine)
    ensure_client_structured_profile_schema(engine)
    with engine.connect() as conn:
        case_cols={row[1] for row in conn.execute(text("PRAGMA table_info(client_cases)"))}
        version_cols={row[1] for row in conn.execute(text("PRAGMA table_info(client_questionnaire_versions)"))}
    assert {"structured_profile_schema_version","structured_profile_version","structured_profile_json"} <= case_cols
    assert {"structured_profile_schema_version","structured_profile_json"} <= version_cols

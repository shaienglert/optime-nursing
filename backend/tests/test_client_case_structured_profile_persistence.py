from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
import app.models.client_case
from app.services.client_case_service import create_client_case, save_questionnaire_version

def test_case_and_history_persist_versioned_structured_profile():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine); db=Session()
    case=create_client_case(db,questionnaire_state={"relationship":"Mother","budget":5000})
    assert case.structured_profile_version==1
    assert "oomnik-structured-profile/" in case.structured_profile_schema_version
    save_questionnaire_version(db,case,{"relationship":"Mother","budget":6000},"Budget changed")
    db.refresh(case)
    assert case.structured_profile_version==2
    assert '"budget"' in (case.structured_profile_json or "")

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


def _new_case_token() -> str:
    # A public, URL-safe case identifier. Deliberately not a sequential/guessable id --
    # each case holds a family's care needs, budget, and medical situation, and this
    # token is the only thing standing between "generate my updated report" and
    # "generate a stranger's".
    return uuid.uuid4().hex


class PersonalReportCase(Base):
    """A remembered request behind a Personal Decision Report.

    Exists so a client can receive an updated report in 24-72h (per the intended
    outreach-and-verify workflow) without re-entering their whole questionnaire.
    Stores only the inputs to run_patient_decision_engine -- an updated report is
    always generated fresh against current facility data at request time, never
    served from a stale cached decision_result.
    """

    __tablename__ = "personal_report_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_token = Column(String(32), nullable=False, unique=True, index=True, default=_new_case_token)
    questionnaire_state_json = Column(Text, nullable=False)
    natural_language_query = Column(Text, nullable=False, default="")
    limit = Column(Integer, nullable=False, default=50)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PersonalReportSnapshot(Base):
    """One generated report for a case, kept for future before/after comparison."""

    __tablename__ = "personal_report_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("personal_report_cases.id"), nullable=False, index=True)
    report_ready = Column(Boolean, nullable=False, default=False)
    report_json = Column(Text, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

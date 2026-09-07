from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum as SAEnum, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class DeferredReportStatus(str, PyEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"


class DeferredDecisionReport(Base):
    """A family who was shown an unranked set and asked to be sent the real one.

    Stored rather than retried in the request because the whole point is that the family
    does not have to wait or come back. The row holds exactly what is needed to run their
    search again and nothing else -- the questionnaire and query they already submitted,
    and one address to send the result to.
    """

    __tablename__ = "deferred_decision_reports"
    __table_args__ = (
        Index("ix_deferred_reports_status_requested", "status", "requested_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    # The exact inputs of the degraded run. Re-running from these is what makes the
    # delivered report the one this family actually asked for.
    questionnaire_json = Column(Text, nullable=False)
    query_text = Column(Text, nullable=False)
    market = Column(String(40), nullable=True)
    result_limit = Column(Integer, nullable=False, default=5)

    # Why their first attempt degraded, kept so a pattern across rows is visible.
    degraded_reason = Column(String(200), nullable=True)
    eligible_at_request = Column(Integer, nullable=True)

    status = Column(
        SAEnum(DeferredReportStatus, name="deferred_report_status_enum", native_enum=False),
        nullable=False,
        default=DeferredReportStatus.PENDING,
        index=True,
    )
    attempts = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    # Set only when a retry produced a genuinely ranked result and the mail was accepted.
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

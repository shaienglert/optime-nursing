from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class CompetitiveIntelligenceSignal(Base):
    """One tracked (competitor, source page, signal type) fact, re-checked on every
    cycle. Kept as a live row per signal (not an append-only log) so each cycle can
    tell, honestly, whether something actually changed since last time or whether
    this is the first-ever observation -- a real "no prior baseline" is different
    from "unchanged," and this table is what lets the agent say which one is true
    instead of guessing.
    """

    __tablename__ = "competitive_intelligence_signals"

    id = Column(Integer, primary_key=True, index=True)
    competitor_key = Column(String(64), nullable=False, index=True)
    competitor_name = Column(String(120), nullable=False)
    signal_type = Column(String(64), nullable=False)
    source_url = Column(Text, nullable=False)
    detail_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    first_observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_observed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_changed_at = Column(DateTime(timezone=True), nullable=True)

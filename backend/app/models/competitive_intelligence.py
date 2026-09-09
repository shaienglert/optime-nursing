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


class MarketSupplySignal(Base):
    """One real news item about senior-living supply -- a construction start, a
    planned/actual opening, or a reported occupancy rate -- found via live search,
    with its real source URL and an extracted snippet, never a fabricated summary.

    Unlike CompetitiveIntelligenceSignal (one live row per tracked fact, updated in
    place), this is append-only and deduplicated by source URL: each article is its
    own event, not a slot whose value changes over time.
    """

    __tablename__ = "market_supply_signals"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(32), nullable=False, index=True)
    headline = Column(String(300), nullable=False)
    snippet = Column(Text, nullable=False)
    city_state = Column(String(80), nullable=True)
    # Structured market intelligence is deliberately separate from recommendation
    # evidence.  These fields describe a reported development event; none of them
    # contributes to a facility score or ranking.
    market_key = Column(String(80), nullable=True, index=True)
    project_name = Column(String(300), nullable=True)
    service_lines = Column(String(160), nullable=True)
    units_or_beds = Column(Integer, nullable=True)
    expected_opening = Column(String(40), nullable=True)
    occupancy_rate = Column(String(32), nullable=True)
    occupancy_period = Column(String(40), nullable=True)
    evidence_status = Column(String(32), nullable=False, default="REPORTED")
    nursing_relevance = Column(String(32), nullable=False, default="UNCLASSIFIED")
    source_url = Column(Text, nullable=False)
    source_domain = Column(String(160), nullable=False)
    first_observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

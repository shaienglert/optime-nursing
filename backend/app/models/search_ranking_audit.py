"""Durable staff-only projection of a completed search, independent of handle TTL."""
from sqlalchemy import Column, Float, String, Text

from app.database import Base


class SearchRankingAudit(Base):
    __tablename__ = "search_ranking_audits"

    id = Column(String(36), primary_key=True)
    decision_token_hash = Column(String(64), nullable=False, index=True)
    created_at_epoch = Column(Float, nullable=False, index=True)
    payload_json = Column(Text, nullable=False)

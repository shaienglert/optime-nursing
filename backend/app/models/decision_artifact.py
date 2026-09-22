"""Opaque, expiring server artifacts shared by all application workers."""
from sqlalchemy import Column, Float, Integer, String, Text

from app.database import Base


class DecisionArtifact(Base):
    __tablename__ = "decision_artifacts"

    token_hash = Column(String(64), primary_key=True)
    inputs_fingerprint = Column(String(80), nullable=False)
    schema_version = Column(Integer, nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at_epoch = Column(Float, nullable=False)
    expires_at_epoch = Column(Float, nullable=False, index=True)

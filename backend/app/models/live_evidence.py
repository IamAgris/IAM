"""Live evidence cache model (proposed Doc 32 §7).

Query-level cache only. Source reputation and claim labels remain in the
existing IICS registry; this table never stores trusted knowledge.
"""

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class LiveEvidenceCache(Base):  # type: ignore[misc]
    __tablename__ = "live_evidence_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_hash = Column(String(64), nullable=False, unique=True, index=True)
    query = Column(Text, nullable=False)
    provider = Column(Text, nullable=False, default="unavailable")
    results = Column(JSON, nullable=False, default=list)
    errors = Column(JSON, nullable=False, default=list)
    freshness_class = Column(String(16), nullable=False, default="current")
    retrieved_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    hit_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

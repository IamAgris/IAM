"""Banking consent records (OD-24) — signed, scoped and revocable."""

from sqlalchemy import Column, Text, JSON, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class BankingConsent(Base):  # type: ignore[misc]
    __tablename__ = "banking_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution = Column(Text, nullable=False)
    account_ref = Column(Text, nullable=False)
    capabilities = Column(JSON, nullable=False, default=list)
    authorization_id = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

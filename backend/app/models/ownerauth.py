"""Owner authorization model — human-controlled authority grants."""

from sqlalchemy import Column, String, Text, JSON, Boolean, DateTime, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class OwnerAuthorization(Base):
    """A standing or one-time authorization granted by the human owner."""
    __tablename__ = "owner_authorizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(Text, nullable=False, index=True)
    max_authority_level = Column(String(1), nullable=False, default="4")
    spending_limit_usd = Column(Numeric(15, 4), nullable=True)
    can_create_accounts = Column(Boolean, nullable=False, default=False)
    can_publish_externally = Column(Boolean, nullable=False, default=False)
    can_modify_own_security = Column(Boolean, nullable=False, default=False)
    scope = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    granted_by = Column(Text, nullable=False, default="owner")
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("max_authority_level IN ('1', '2', '3', '4')", name="ck_owner_auth_level"),
    )

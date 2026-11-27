"""Scoped API credentials.

Only a SHA-256 hash of a credential is stored; the plaintext is returned once
at creation. Creator authority remains email + signed challenge (OD-19) and is
never represented by one of these keys.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    key_hash = Column(Text, nullable=False, unique=True, index=True)
    scope = Column(Text, nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Text, nullable=False, default="bootstrap")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "scope IN ('user', 'service', 'operator', 'admin')",
            name="ck_api_credential_scope",
        ),
    )

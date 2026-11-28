"""Encrypted provider-connection credentials for multi-model routing (OD-51).

These rows hold IAM's *gateway* credentials for a provider connection. The
secret is always stored encrypted; the plaintext is never returned by an API
and never written to logs. Provider-side API keys continue to live in the
LiteLLM gateway configuration, so LiteLLM remains the single gateway (OD-38).
"""

import uuid
from typing import Any, Dict

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ModelProviderKey(Base):  # type: ignore[misc]
    """One authorised provider connection key with independent limits/health."""

    __tablename__ = "model_provider_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Text, nullable=False)
    key_alias = Column(Text, nullable=False)
    # Short SHA-256 prefix of the secret. Safe to display and to store in usage.
    key_fingerprint = Column(Text, nullable=False)
    secret_ciphertext = Column(Text, nullable=False)
    scope = Column(Text, nullable=False, default="free")
    is_enabled = Column(Boolean, nullable=False, default=True)
    health = Column(Text, nullable=False, default="unknown")
    failure_count = Column(Integer, nullable=False, default=0)
    monthly_limit_usd = Column(Numeric(12, 6), nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "scope IN ('free', 'paid', 'specialist')", name="ck_model_provider_key_scope"
        ),
        CheckConstraint(
            "health IN ('unknown', 'healthy', 'unhealthy', 'disabled')",
            name="ck_model_provider_key_health",
        ),
    )

    def public_dict(self) -> Dict[str, Any]:
        """Return only non-secret fields. Never include ciphertext or plaintext."""
        return {
            "id": str(self.id),
            "provider": self.provider,
            "key_alias": self.key_alias,
            "key_fingerprint": self.key_fingerprint,
            "scope": self.scope,
            "is_enabled": bool(self.is_enabled),
            "health": self.health,
            "failure_count": self.failure_count,
            "monthly_limit_usd": str(self.monthly_limit_usd) if self.monthly_limit_usd is not None else None,
            "last_checked_at": self.last_checked_at,
            "last_used_at": self.last_used_at,
        }

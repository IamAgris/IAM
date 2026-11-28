"""Human assistance and website credential vault records (Phase 9)."""

from sqlalchemy import Column, Text, JSON, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AssistanceRequest(Base):  # type: ignore[misc]
    """A paused task waiting for a specific level of human participation."""

    __tablename__ = "assistance_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    context = Column(JSON, nullable=False, default=dict)
    task_ref = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    resolved_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class WebsiteCredential(Base):  # type: ignore[misc]
    """Encrypted website credential reference; raw secrets are never logged."""

    __tablename__ = "website_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    username = Column(Text, nullable=False)
    secret_ciphertext = Column(Text, nullable=False)
    secret_env_var = Column(Text, nullable=True)  # name only, when externally supplied
    owner_entity = Column(Text, nullable=False)
    provenance = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

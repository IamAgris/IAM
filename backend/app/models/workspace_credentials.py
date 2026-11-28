"""Per-workspace scoped credentials (WS-03)."""

from sqlalchemy import Column, Text, JSON, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class WorkspaceCredential(Base):  # type: ignore[misc]
    """A short-lived, scoped credential reference.

    ``secret_env_var`` names an environment variable; the secret value is never
    stored in IAM, returned by any API, or written to an audit event.
    """

    __tablename__ = "workspace_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspace_environments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    purpose = Column(Text, nullable=False)
    secret_env_var = Column(Text, nullable=False)
    scopes = Column(JSON, nullable=False, default=dict)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint(
            "purpose IN ('git', 'package_registry', 'api', 'test_fixture')",
            name="ck_workspace_credential_purpose",
        ),
    )

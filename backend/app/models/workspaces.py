"""Workspace manager models (WS-01/WS-02)."""

from sqlalchemy import Column, Text, JSON, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class WorkspaceEnvironment(Base):
    """An isolated, replaceable coding workspace.

    ``isolation`` records the enforced boundary (no protected-core access, no
    default network, non-root execution). ``credential_env_var`` stores only an
    environment-variable *name*, never a secret value.
    """

    __tablename__ = "workspace_environments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    provider = Column(Text, nullable=False, default="local")
    status = Column(Text, nullable=False, default="provisioning")
    isolation = Column(JSON, nullable=False, default=dict)
    credential_env_var = Column(Text, nullable=True)
    directory = Column(Text, nullable=False)
    last_output = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('provisioning', 'active', 'saved', 'destroyed', 'failed')",
            name="ck_workspace_status",
        ),
    )

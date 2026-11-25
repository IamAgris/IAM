"""Protected-core integrity, node attestation and signed sync objects.

Integrity reporting is best-effort: a signed attestation is evidence, not
proof that a machine controlled by somebody else is unmodified.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class IntegrityManifest(Base):
    """Known-good measurement of the protected core, explicitly approved."""

    __tablename__ = "integrity_manifests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(Text, nullable=False)
    root_hash = Column(Text, nullable=False, index=True)
    manifest = Column(JSON, nullable=False)
    signed_by = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NodeAttestation(Base):
    """Signed evidence submitted by a node about its own software state."""

    __tablename__ = "node_attestations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(
        UUID(as_uuid=True),
        ForeignKey("registered_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    public_key = Column(Text, nullable=False)
    core_hash = Column(Text, nullable=False)
    platform_hash = Column(Text, nullable=True)
    signature = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False)
    verified = Column(Boolean, nullable=False, default=False)
    result = Column(Text, nullable=False, default="candidate")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "result IN ('candidate', 'restricted', 'trusted', 'revoked')",
            name="ck_node_attestation_result",
        ),
    )


class SyncObject(Base):
    """Signed, untrusted-by-default knowledge object from a trusted node."""

    __tablename__ = "sync_objects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publisher_node_id = Column(
        UUID(as_uuid=True),
        ForeignKey("registered_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    object_type = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    signature = Column(Text, nullable=False)
    verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

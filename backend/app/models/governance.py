"""Governance engine SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AuthorityBoundary(Base):
    """Four-level authority model enforcement."""
    __tablename__ = "authority_boundaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(Text, nullable=False)
    authority_level = Column(Text, nullable=False)  # 1, 2, 3, 4
    description = Column(Text, nullable=True)
    requires_human_approval = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("authority_level IN ('1', '2', '3', '4')", name="ck_authority_level"),
    )


class ApprovalPolicy(Base):
    """Approval policies for different action types."""
    __tablename__ = "approval_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_category = Column(Text, nullable=False)
    min_authority_level = Column(Text, nullable=False)
    auto_approve_conditions = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("min_authority_level IN ('1', '2', '3', '4')", name="ck_approval_policy_level"),
    )


class SecurityBoundary(Base):
    """Security boundaries IAM cannot cross."""
    __tablename__ = "security_boundaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boundary_name = Column(Text, nullable=False)
    boundary_type = Column(Text, nullable=False)  # financial, security, legal, infrastructure
    description = Column(Text, nullable=False)
    is_immutable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

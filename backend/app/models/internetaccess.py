"""IAM Internet Access and Digital Interaction System models.

Public exploration is open; consequential actions are permission-gated.
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class InternetSession(Base):
    """A browser session for navigating the open internet."""
    __tablename__ = "internet_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token = Column(String(64), nullable=False, unique=True, index=True)
    purpose = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    actions = relationship("BrowserAction", back_populates="session", cascade="all, delete-orphan")


class BrowserAction(Base):
    """Recorded browser interaction — navigate, click, type, submit."""
    __tablename__ = "browser_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("internet_sessions.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(Text, nullable=False)  # navigate, click, type, submit, screenshot, scroll
    target = Column(Text, nullable=True)  # url, selector, or element ref
    value = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    permission_required = Column(Boolean, nullable=False, default=False)
    authorized = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("action_type IN ('navigate', 'click', 'type', 'submit', 'screenshot', 'scroll', 'text', 'links')", name="ck_browser_action_type"),
    )

    session = relationship("InternetSession", back_populates="actions")


class OnlineAccount(Base):
    """IAM's authorised online accounts and profiles."""
    __tablename__ = "online_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(Text, nullable=False)
    account_identifier = Column(Text, nullable=True)
    account_type = Column(Text, nullable=False, default="service")  # service, community, social, business
    is_authorised = Column(Boolean, nullable=False, default=False)
    authorised_by = Column(Text, nullable=True)
    credential_reference = Column(Text, nullable=True)  # secret store reference, never raw secret
    credential_rotated_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("account_type IN ('service', 'community', 'social', 'business')", name="ck_online_account_type"),
    )


class PublishedContent(Base):
    """Content published with approval."""
    __tablename__ = "published_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)  # article, post, website, product, code
    target_platform = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    is_authorised = Column(Boolean, nullable=False, default=False)
    authorised_by = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("content_type IN ('article', 'post', 'website', 'product', 'code')", name="ck_published_content_type"),
    )


class MonitoredTarget(Base):
    """Websites, services and developments IAM monitors."""
    __tablename__ = "monitored_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_url = Column(Text, nullable=False)
    target_type = Column(Text, nullable=False, default="website")  # website, service, news, competitor
    check_interval_minutes = Column(Integer, nullable=False, default=60)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    config = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint("target_type IN ('website', 'service', 'news', 'competitor')", name="ck_monitored_target_type"),
    )


class RetrievedFile(Base):
    """Files downloaded and analysed from the internet."""
    __tablename__ = "retrieved_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(Text, nullable=False)
    filename = Column(Text, nullable=True)
    content_type = Column(Text, nullable=True)
    storage_path = Column(Text, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    scan_status = Column(Text, nullable=False, default="pending")  # pending, clean, suspicious
    retrieved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("scan_status IN ('pending', 'clean', 'suspicious')", name="ck_retrieved_file_scan"),
    )


class InternetPermission(Base):
    """Permission gates: public exploration open, consequential actions gated."""
    __tablename__ = "internet_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(Text, nullable=False, unique=True)
    category = Column(Text, nullable=False)  # exploration, communication, financial, publishing, account
    is_autonomous = Column(Boolean, nullable=False, default=False)
    # Legacy DB column name retained; authority now comes from signed Creator approvals.
    requires_creator_authorization = Column(
        "requires_owner_authorization", Boolean, nullable=False, default=True
    )
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("category IN ('exploration', 'communication', 'financial', 'publishing', 'account')", name="ck_internet_permission_category"),
    )


class InternetEvent(Base):
    """Audit trail of internet activity."""
    __tablename__ = "internet_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(Text, nullable=False)
    target = Column(Text, nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    risk_level = Column(Text, nullable=False, default="low")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="ck_internet_event_risk"),
    )

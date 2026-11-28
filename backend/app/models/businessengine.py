"""Business engine SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class BusinessBudget(Base):  # type: ignore[misc]
    """Per-business budget tracking."""
    __tablename__ = "business_budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_project_id = Column(UUID(as_uuid=True), ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(15, 4), nullable=False)
    period = Column(Text, nullable=False)
    is_approved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_business_budget_amount"),
    )


class CustomerRecord(Base):  # type: ignore[misc]
    """Customer tracking for business projects."""
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_project_id = Column(UUID(as_uuid=True), ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    email = Column(Text, nullable=True)
    company = Column(Text, nullable=True)
    total_spent = Column(Numeric(15, 4), nullable=False, default=0)
    customer_since = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_purchase_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("total_spent >= 0", name="ck_customer_total_spent"),
    )


class SalesRecord(Base):  # type: ignore[misc]
    """Sales tracking for business projects."""
    __tablename__ = "sales_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_project_id = Column(UUID(as_uuid=True), ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(15, 4), nullable=False)
    currency = Column(Text, nullable=False, default="USD")
    product_or_service = Column(Text, nullable=False)
    sold_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_sales_amount"),
    )


class BusinessReport(Base):  # type: ignore[misc]
    """Business plans and reports."""
    __tablename__ = "business_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_project_id = Column(UUID(as_uuid=True), ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(Text, nullable=False)  # plan, performance, review, closure
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_approved = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint("report_type IN ('plan', 'performance', 'review', 'closure')", name="ck_business_report_type"),
    )


class ProjectPortfolio(Base):  # type: ignore[misc]
    """Multiple project management."""
    __tablename__ = "project_portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    total_projects = Column(Integer, nullable=False, default=0)
    active_projects = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

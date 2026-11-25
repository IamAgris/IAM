"""Business and finance module SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class BusinessOpportunity(Base):
    __tablename__ = "business_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    estimated_revenue = Column(Numeric(15, 4), nullable=True)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.5)
    status = Column(Text, nullable=False, default="identified")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_opportunity_confidence"),
        CheckConstraint("status IN ('identified', 'evaluating', 'pursuing', 'rejected', 'completed')", name="ck_opportunity_status"),
    )

    projects = relationship("BusinessProject", back_populates="opportunity")


class BusinessProject(Base):
    __tablename__ = "business_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("business_opportunities.id", ondelete="SET NULL"), nullable=True)
    status = Column(Text, nullable=False, default="planning")
    revenue = Column(Numeric(15, 4), nullable=False, default=0)
    expenses = Column(Numeric(15, 4), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('planning', 'active', 'completed', 'paused', 'cancelled')", name="ck_business_project_status"),
    )

    opportunity = relationship("BusinessOpportunity", back_populates="projects")
    performance = relationship("BusinessPerformance", back_populates="project", cascade="all, delete-orphan")


class BusinessPerformance(Base):
    __tablename__ = "business_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False)
    period = Column(Text, nullable=False)
    revenue = Column(Numeric(15, 4), nullable=False, default=0)
    expenses = Column(Numeric(15, 4), nullable=False, default=0)
    profit = Column(Numeric(15, 4), nullable=False, default=0)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("BusinessProject", back_populates="performance")


class FinancialLedger(Base):
    __tablename__ = "financial_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("financial_transactions.id", ondelete="CASCADE"), nullable=False)
    account = Column(Text, nullable=False)
    debit_amount = Column(Numeric(15, 4), nullable=False, default=0)
    credit_amount = Column(Numeric(15, 4), nullable=False, default=0)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FinancialBudget(Base):
    __tablename__ = "financial_budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(15, 4), nullable=False)
    period = Column(Text, nullable=False)
    is_approved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount = Column(Numeric(15, 4), nullable=False)
    currency = Column(Text, nullable=False, default="USD")
    type = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    reference_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense', 'transfer')", name="ck_transaction_type"),
    )

    ledger_entries = relationship("FinancialLedger", backref="transaction", cascade="all, delete-orphan")


class CryptoActivity(Base):
    __tablename__ = "crypto_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("financial_transactions.id", ondelete="SET NULL"), nullable=True)
    blockchain = Column(Text, nullable=True)
    asset = Column(Text, nullable=True)
    amount = Column(Numeric(20, 8), nullable=True)
    address = Column(Text, nullable=True)
    tx_hash = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OperatingExpense(Base):
    __tablename__ = "operating_expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(15, 4), nullable=False)
    description = Column(Text, nullable=True)
    incurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

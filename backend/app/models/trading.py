"""Paper-trading simulation records (Doc 25) — never real orders."""

from sqlalchemy import Column, Text, JSON, Boolean, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class PaperPortfolio(Base):
    __tablename__ = "paper_portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    cash_balance = Column(Numeric(15, 4), nullable=False, default=0)
    holdings = Column(JSON, nullable=False, default=dict)
    risk_limits = Column(JSON, nullable=False, default=dict)
    emergency_stop = Column(Boolean, nullable=False, default=False)
    simulation_only = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(
        UUID(as_uuid=True), ForeignKey("paper_portfolios.id", ondelete="CASCADE"), nullable=False
    )
    symbol = Column(Text, nullable=False)
    side = Column(Text, nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(15, 4), nullable=False)
    notional = Column(Numeric(15, 4), nullable=False)
    fee = Column(Numeric(15, 4), nullable=False, default=0)
    status = Column(Text, nullable=False, default="simulated")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

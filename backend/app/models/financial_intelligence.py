"""Doc 25 Amendment A — research-only financial intelligence records.

Prediction markets, gaming/casino intelligence and investment research are
stored here as research and analysis only. No table in this module holds an
order, wager, wallet funding instruction or executable trading authority.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class PredictionMarket(Base):  # type: ignore[misc]
    """A public event contract discovered for research (never an open position)."""

    __tablename__ = "prediction_markets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(Text, nullable=False)
    market_ref = Column(Text, nullable=False)
    event_name = Column(Text, nullable=False)
    outcomes = Column(JSON, nullable=False, default=list)
    implied_probabilities = Column(JSON, nullable=False, default=dict)
    source_url = Column(Text, nullable=True)
    legal_status = Column(Text, nullable=False, default="research_only")
    real_money_enabled = Column(Boolean, nullable=False, default=False)
    observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("platform", "market_ref", name="uq_prediction_market_ref"),
        CheckConstraint(
            "legal_status IN ('research_only', 'legal_review_required', 'cleared')",
            name="ck_prediction_market_legal_status",
        ),
    )


class ProbabilityEstimate(Base):  # type: ignore[misc]
    """IAM's independent probability estimate for one market outcome."""

    __tablename__ = "probability_estimates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prediction_markets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outcome = Column(Text, nullable=False)
    iam_probability = Column(Numeric(5, 4), nullable=False)
    evidence = Column(JSON, nullable=False, default=list)
    analyst = Column(Text, nullable=False, default="iam")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "iam_probability >= 0 AND iam_probability <= 1",
            name="ck_probability_estimate_range",
        ),
    )


class ForecastRun(Base):  # type: ignore[misc]
    """A documented IAM probability forecast, independent of market prices."""

    __tablename__ = "forecast_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prediction_markets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method = Column(Text, nullable=False)
    inputs = Column(JSON, nullable=False, default=dict)
    probabilities = Column(JSON, nullable=False, default=dict)
    evidence = Column(JSON, nullable=False, default=list)
    rationale = Column(Text, nullable=False)
    confidence = Column(Numeric(3, 3), nullable=False, default=0)
    market_implied_probabilities_used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "method IN ('evidence_weighted', 'base_rate')",
            name="ck_forecast_run_method",
        ),
    )


class GamingResearchRecord(Base):  # type: ignore[misc]
    """Mathematical study of a casino game — no wagering capability."""

    __tablename__ = "gaming_research_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game = Column(Text, nullable=False)
    provider = Column(Text, nullable=True)
    rtp = Column(Numeric(5, 4), nullable=False)
    house_edge = Column(Numeric(5, 4), nullable=False)
    sample_size = Column(Integer, nullable=False, default=0)
    methodology = Column(Text, nullable=False)
    findings = Column(JSON, nullable=False, default=dict)
    wagering_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("rtp >= 0 AND rtp <= 1", name="ck_gaming_rtp_range"),
        CheckConstraint(
            "house_edge >= 0 AND house_edge <= 1", name="ck_gaming_house_edge_range"
        ),
        CheckConstraint("sample_size >= 0", name="ck_gaming_sample_size"),
    )


class InvestmentResearchRecord(Base):  # type: ignore[misc]
    """Research note or proposal for an authorised investment market."""

    __tablename__ = "investment_research_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_class = Column(Text, nullable=False)
    symbol = Column(Text, nullable=False)
    thesis = Column(Text, nullable=False)
    risk_notes = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=False, default=dict)
    execution_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "asset_class IN ('stocks', 'etfs', 'commodities', 'futures', 'bonds', "
            "'precious_metals', 'indices', 'portfolio')",
            name="ck_investment_asset_class",
        ),
    )


class ProviderRegistryEntry(Base):  # type: ignore[misc]
    """§18 provider gates recorded before any adapter is enabled."""

    __tablename__ = "provider_registry_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    access_model = Column(Text, nullable=False, default="free")
    documented_api_and_auth = Column(Boolean, nullable=False, default=False)
    commercial_use = Column(Boolean, nullable=False, default=False)
    automated_use = Column(Boolean, nullable=False, default=False)
    south_africa_supported = Column(Boolean, nullable=False, default=False)
    sandbox_available = Column(Boolean, nullable=False, default=False)
    licence_required = Column(Boolean, nullable=False, default=False)
    licence_requirements_recorded = Column(Boolean, nullable=False, default=False)
    gates_reviewed = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    adapter_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("name", name="uq_provider_registry_name"),
        CheckConstraint(
            "access_model IN ('free', 'paid', 'mixed')",
            name="ck_provider_access_model",
        ),
    )

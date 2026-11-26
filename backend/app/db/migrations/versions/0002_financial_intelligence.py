"""Doc 25 Amendment A — research-only financial intelligence tables.

Separate revision so the generated 0001 baseline is left untouched. No table
here stores an order, wager, wallet funding instruction or execution authority.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_financial_intelligence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade():
    op.create_table(
        "prediction_markets",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("market_ref", sa.Text(), nullable=False),
        sa.Column("event_name", sa.Text(), nullable=False),
        sa.Column("outcomes", sa.JSON(), nullable=False),
        sa.Column("implied_probabilities", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("legal_status", sa.Text(), nullable=False, server_default="research_only"),
        sa.Column("real_money_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("platform", "market_ref", name="uq_prediction_market_ref"),
        sa.CheckConstraint(
            "legal_status IN ('research_only', 'legal_review_required', 'cleared')",
            name="ck_prediction_market_legal_status",
        ),
    )
    op.create_table(
        "probability_estimates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "market_id",
            UUID,
            sa.ForeignKey("prediction_markets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("iam_probability", sa.Numeric(5, 4), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("analyst", sa.Text(), nullable=False, server_default="iam"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "iam_probability >= 0 AND iam_probability <= 1",
            name="ck_probability_estimate_range",
        ),
    )
    op.create_index(
        "ix_probability_estimates_market_id",
        "probability_estimates",
        ["market_id"],
    )
    op.create_table(
        "forecast_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "market_id",
            UUID,
            sa.ForeignKey("prediction_markets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("probabilities", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 3), nullable=False, server_default="0"),
        sa.Column(
            "market_implied_probabilities_used",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "method IN ('evidence_weighted', 'base_rate')", name="ck_forecast_run_method"
        ),
    )
    op.create_index("ix_forecast_runs_market_id", "forecast_runs", ["market_id"])
    op.create_table(
        "gaming_research_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("game", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("rtp", sa.Numeric(5, 4), nullable=False),
        sa.Column("house_edge", sa.Numeric(5, 4), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("methodology", sa.Text(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("wagering_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rtp >= 0 AND rtp <= 1", name="ck_gaming_rtp_range"),
        sa.CheckConstraint(
            "house_edge >= 0 AND house_edge <= 1", name="ck_gaming_house_edge_range"
        ),
        sa.CheckConstraint("sample_size >= 0", name="ck_gaming_sample_size"),
    )
    op.create_table(
        "investment_research_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("asset_class", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("risk_notes", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("execution_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "asset_class IN ('stocks', 'etfs', 'commodities', 'futures', 'bonds', "
            "'precious_metals', 'indices', 'portfolio')",
            name="ck_investment_asset_class",
        ),
    )
    op.create_table(
        "provider_registry_entries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("access_model", sa.Text(), nullable=False, server_default="free"),
        sa.Column("documented_api_and_auth", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("commercial_use", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("automated_use", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("south_africa_supported", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sandbox_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("licence_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("licence_requirements_recorded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gates_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("adapter_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", name="uq_provider_registry_name"),
        sa.CheckConstraint(
            "access_model IN ('free', 'paid', 'mixed')", name="ck_provider_access_model"
        ),
    )


def downgrade():
    op.drop_table("provider_registry_entries")
    op.drop_table("investment_research_records")
    op.drop_table("gaming_research_records")
    op.drop_index("ix_forecast_runs_market_id", table_name="forecast_runs")
    op.drop_table("forecast_runs")
    op.drop_index("ix_probability_estimates_market_id", table_name="probability_estimates")
    op.drop_table("probability_estimates")
    op.drop_table("prediction_markets")

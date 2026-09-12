"""Adiciona patrimônio, históricos e snapshots mensais.

Revision ID: 20260911_0005
Revises: 20260911_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0005"
down_revision: str | Sequence[str] | None = "20260911_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("current_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("external_ref", sa.String(100)),
        sa.Column("valued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "type IN ('cash', 'investment', 'real_estate', 'pension')", name="ck_asset_type"
        ),
        sa.CheckConstraint("source IN ('manual', 'pluggy')", name="ck_asset_source"),
        sa.CheckConstraint("current_value >= 0", name="ck_asset_current_value"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_ref"),
    )
    op.create_index("ix_assets_household_id", "assets", ["household_id"])

    op.create_table(
        "liabilities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("current_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("original_amount", sa.Numeric(18, 2)),
        sa.Column("interest_rate", sa.Numeric(10, 4)),
        sa.Column("monthly_payment", sa.Numeric(18, 2)),
        sa.Column("due_day", sa.Integer()),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("external_ref", sa.String(100)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "type IN ('financing', 'credit_card', 'loan')", name="ck_liability_type"
        ),
        sa.CheckConstraint("source IN ('manual', 'pluggy')", name="ck_liability_source"),
        sa.CheckConstraint("current_balance >= 0", name="ck_liability_current_balance"),
        sa.CheckConstraint(
            "original_amount IS NULL OR original_amount >= 0",
            name="ck_liability_original_amount",
        ),
        sa.CheckConstraint(
            "interest_rate IS NULL OR interest_rate >= 0", name="ck_liability_interest_rate"
        ),
        sa.CheckConstraint(
            "monthly_payment IS NULL OR monthly_payment >= 0",
            name="ck_liability_monthly_payment",
        ),
        sa.CheckConstraint(
            "due_day IS NULL OR due_day BETWEEN 1 AND 31", name="ck_liability_due_day"
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_ref"),
    )
    op.create_index("ix_liabilities_household_id", "liabilities", ["household_id"])

    op.create_table(
        "asset_value_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_value_history_asset_id", "asset_value_history", ["asset_id"])
    op.create_index("ix_asset_value_history_recorded_at", "asset_value_history", ["recorded_at"])

    op.create_table(
        "liability_value_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("liability_id", sa.Uuid(), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["liability_id"], ["liabilities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_liability_value_history_liability_id",
        "liability_value_history",
        ["liability_id"],
    )
    op.create_index(
        "ix_liability_value_history_recorded_at",
        "liability_value_history",
        ["recorded_at"],
    )

    op.create_table(
        "net_worth_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("ref_month", sa.Date(), nullable=False),
        sa.Column("total_assets", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_liabilities", sa.Numeric(18, 2), nullable=False),
        sa.Column("net_worth", sa.Numeric(18, 2), nullable=False),
        sa.Column("debt_ratio", sa.Numeric(12, 6)),
        sa.Column("savings_rate", sa.Numeric(12, 6)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "ref_month"),
    )
    op.create_index("ix_net_worth_snapshots_household_id", "net_worth_snapshots", ["household_id"])
    op.create_index("ix_net_worth_snapshots_ref_month", "net_worth_snapshots", ["ref_month"])


def downgrade() -> None:
    op.drop_table("net_worth_snapshots")
    op.drop_table("liability_value_history")
    op.drop_table("asset_value_history")
    op.drop_table("liabilities")
    op.drop_table("assets")

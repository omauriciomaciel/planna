"""Guarda histórico de saldos para variação patrimonial.

Revision ID: 20260911_0003
Revises: 20260911_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0003"
down_revision: str | Sequence[str] | None = "20260911_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_balance_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_balance_snapshots_account_id", "account_balance_snapshots", ["account_id"]
    )
    op.create_index(
        "ix_account_balance_snapshots_recorded_at", "account_balance_snapshots", ["recorded_at"]
    )


def downgrade() -> None:
    op.drop_table("account_balance_snapshots")

"""Adiciona Open Finance e categorização.

Revision ID: 20260911_0002
Revises: 20260911_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0002"
down_revision: str | Sequence[str] | None = "20260911_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pluggy_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("pluggy_item_id", sa.String(64), nullable=False),
        sa.Column("connector_id", sa.String(64)),
        sa.Column("institution_name", sa.String(160), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("execution_status", sa.String(80)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pluggy_item_id"),
    )
    op.create_index("ix_pluggy_items_household_id", "pluggy_items", ["household_id"])
    op.create_index("ix_pluggy_items_pluggy_item_id", "pluggy_items", ["pluggy_item_id"])
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid()),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("parent_id", sa.Uuid()),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("color", sa.String(32)),
        sa.Column("icon", sa.String(40)),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("external_id", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('expense', 'income')", name="ck_category_kind"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_categories_household_id", "categories", ["household_id"])
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("pluggy_account_id", sa.String(64), nullable=False),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("subtype", sa.String(50)),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("number_masked", sa.String(80)),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("credit_limit", sa.Numeric(18, 2)),
        sa.Column("due_day", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("type IN ('bank', 'credit', 'investment')", name="ck_account_type"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["pluggy_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pluggy_account_id"),
    )
    op.create_index("ix_accounts_household_id", "accounts", ["household_id"])
    op.create_index("ix_accounts_pluggy_account_id", "accounts", ["pluggy_account_id"])
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("pluggy_transaction_id", sa.String(64), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("merchant_name", sa.String(200)),
        sa.Column("merchant_cnpj", sa.String(20)),
        sa.Column("category_id", sa.Uuid()),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("installment_current", sa.Integer()),
        sa.Column("installment_total", sa.Integer()),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("type IN ('debit', 'credit')", name="ck_transaction_type"),
        sa.CheckConstraint("status IN ('posted', 'pending')", name="ck_transaction_status"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pluggy_transaction_id"),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_index("ix_transactions_pluggy_transaction_id", "transactions", ["pluggy_transaction_id"])


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("accounts")
    op.drop_table("categories")
    op.drop_table("pluggy_items")

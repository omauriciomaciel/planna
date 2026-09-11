"""Adiciona notas SEFAZ e despesas de vale.

Revision ID: 20260911_0004
Revises: 20260911_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0004"
down_revision: str | Sequence[str] | None = "20260911_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("access_key", sa.String(44), nullable=False),
        sa.Column("number", sa.String(20)),
        sa.Column("series", sa.String(10)),
        sa.Column("issue_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("merchant_cnpj", sa.String(14)),
        sa.Column("merchant_name", sa.String(200), nullable=False),
        sa.Column("merchant_address", sa.String(500)),
        sa.Column("source_url", sa.String(4096), nullable=False),
        sa.Column("payment_method_raw", sa.String(120)),
        sa.Column("payment_status", sa.String(16), nullable=False),
        sa.Column("matched_transaction_id", sa.Uuid()),
        sa.Column("match_confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column("protocol", sa.String(100)),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "payment_status IN ('reconciled', 'voucher')", name="ck_invoice_payment_status"
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["matched_transaction_id"], ["transactions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("access_key"),
        sa.UniqueConstraint("matched_transaction_id"),
    )
    op.create_index("ix_invoices_household_id", "invoices", ["household_id"])
    op.create_index("ix_invoices_issue_datetime", "invoices", ["issue_datetime"])
    op.create_index("ix_invoices_merchant_cnpj", "invoices", ["merchant_cnpj"])

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("product_code", sa.String(80)),
        sa.Column("ncm", sa.String(16)),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit", sa.String(20)),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("category_id", sa.Uuid()),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_items_category_id", "invoice_items", ["category_id"])
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])

    op.alter_column("transactions", "account_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column(
        "transactions", "pluggy_transaction_id", existing_type=sa.String(64), nullable=True
    )
    op.add_column("transactions", sa.Column("source_invoice_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_transactions_source_invoice_id",
        "transactions",
        "invoices",
        ["source_invoice_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_transactions_source_invoice_id", "transactions", ["source_invoice_id"]
    )


def downgrade() -> None:
    op.execute("DELETE FROM transactions WHERE source = 'voucher'")
    op.drop_constraint("uq_transactions_source_invoice_id", "transactions", type_="unique")
    op.drop_constraint("fk_transactions_source_invoice_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "source_invoice_id")
    op.alter_column(
        "transactions", "pluggy_transaction_id", existing_type=sa.String(64), nullable=False
    )
    op.alter_column("transactions", "account_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_table("invoice_items")
    op.drop_table("invoices")

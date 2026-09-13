"""Classifica transações para separar fluxo de caixa de consumo."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_0008"
down_revision: str | Sequence[str] | None = "20260912_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("economic_type", sa.String(24)))
    op.create_index("ix_transactions_economic_type", "transactions", ["economic_type"])
    op.execute(
        sa.text(
            """
            UPDATE transactions AS t
            SET economic_type = CASE
                WHEN t.source = 'voucher' AND t.type = 'debit' THEN 'voucher_expense'
                WHEN lower(coalesce(c.name, '')) IN ('transfer', 'transfers', 'same person transfer')
                  OR lower(t.description) LIKE '%same person transfer%'
                  OR lower(t.description) LIKE '%internal transfer%' THEN 'transfer'
                WHEN t.type = 'debit' AND lower(coalesce(c.name, '')) IN
                  ('credit card payment', 'card payment') THEN 'card_payment'
                WHEN t.type = 'credit' AND (
                  lower(t.description) LIKE '%refund%'
                  OR lower(t.description) LIKE '%reversal%'
                  OR lower(t.description) LIKE '%estorno%'
                  OR lower(t.description) LIKE '%reembolso%'
                ) THEN 'refund'
                WHEN t.type = 'credit' AND lower(coalesce(c.name, '')) IN ('salary', 'payroll') THEN 'salary'
                WHEN t.type = 'credit' AND lower(coalesce(c.name, '')) IN
                  ('food allowance', 'meal voucher', 'vale alimentacao', 'vale refeicao') THEN 'benefit'
                WHEN t.type = 'debit' AND lower(coalesce(c.name, '')) IN ('investment', 'investments') THEN 'investment'
                WHEN t.type = 'credit' THEN 'other_income'
                ELSE 'expense'
            END
            FROM categories AS c
            WHERE c.id = t.category_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE transactions
            SET economic_type = CASE WHEN type = 'credit' THEN 'other_income' ELSE 'expense' END
            WHERE economic_type IS NULL
            """
        )
    )
    for old_name, new_name in {
        "Travel": "Viagens",
        "Transportation": "Transporte",
        "Online Services": "Serviços Online",
        "Restaurants": "Restaurantes",
        "Groceries": "Mercado",
        "Health": "Saúde",
        "Education": "Educação",
        "Entertainment": "Entretenimento",
        "Shopping": "Compras",
        "Bills & Utilities": "Contas e Serviços",
        "Transfer": "Transferências",
        "Salary": "Salário",
        "Cash": "Saque",
        "Same person transfer": "Transferência entre contas",
        "Investment": "Investimentos",
        "Insurance": "Seguros",
        "Taxes": "Impostos",
        "Home": "Moradia",
        "Personal Care": "Cuidados Pessoais",
        "Clothing": "Vestuário",
        "Electronics": "Eletrônicos",
        "Subscriptions": "Assinaturas",
        "Pets": "Pets",
        "Other": "Outros",
    }.items():
        op.execute(
            sa.text(
                "UPDATE categories SET name = :new_name "
                "WHERE name = :old_name AND is_system = true AND household_id IS NULL"
            ).bindparams(old_name=old_name, new_name=new_name)
        )


def downgrade() -> None:
    op.drop_index("ix_transactions_economic_type", table_name="transactions")
    op.drop_column("transactions", "economic_type")

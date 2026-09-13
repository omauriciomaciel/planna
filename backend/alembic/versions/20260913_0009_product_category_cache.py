"""Cache de categorias de produtos de notas fiscais."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_0009"
down_revision: str | Sequence[str] | None = "20260913_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_category_cache",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("product_code", sa.String(80), unique=True, nullable=True),
        sa.Column("normalized_description", sa.String(500), nullable=False),
        sa.Column("category_name", sa.String(100), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="llm"),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_product_category_cache_product_code", "product_category_cache", ["product_code"]
    )
    op.create_index(
        "ix_product_category_cache_normalized_description",
        "product_category_cache",
        ["normalized_description"],
    )


def downgrade() -> None:
    op.drop_table("product_category_cache")

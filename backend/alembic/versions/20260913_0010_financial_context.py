"""Contexto livre informado pelo domicílio."""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0010"
down_revision: str | Sequence[str] | None = "20260913_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("households", sa.Column("financial_context", sa.String(1000)))

def downgrade() -> None:
    op.drop_column("households", "financial_context")

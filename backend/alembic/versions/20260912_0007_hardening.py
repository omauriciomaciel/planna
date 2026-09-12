"""Registra aceite de privacidade e consentimento para IA.

Revision ID: 20260912_0007
Revises: 20260912_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260912_0007"
down_revision: str | Sequence[str] | None = "20260912_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("privacy_accepted_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("privacy_version", sa.String(16)))
    op.add_column("users", sa.Column("ai_consent_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("users", "ai_consent_at")
    op.drop_column("users", "privacy_version")
    op.drop_column("users", "privacy_accepted_at")

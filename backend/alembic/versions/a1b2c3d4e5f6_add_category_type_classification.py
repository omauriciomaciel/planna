"""add category_type and classification to categories

Revision ID: a1b2c3d4e5f6
Revises: 67bb15026915
Create Date: 2026-02-27 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '67bb15026915'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

categorytype = sa.Enum('income', 'expense', name='categorytype')
categoryclassification = sa.Enum('essential', 'non_essential', name='categoryclassification')


def upgrade() -> None:
    categorytype.create(op.get_bind(), checkfirst=True)
    categoryclassification.create(op.get_bind(), checkfirst=True)
    op.add_column('categories', sa.Column('category_type', categorytype, nullable=True))
    op.add_column('categories', sa.Column('classification', categoryclassification, nullable=True))


def downgrade() -> None:
    op.drop_column('categories', 'classification')
    op.drop_column('categories', 'category_type')
    categoryclassification.drop(op.get_bind(), checkfirst=True)
    categorytype.drop(op.get_bind(), checkfirst=True)

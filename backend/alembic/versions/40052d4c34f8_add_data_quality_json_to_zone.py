"""add data quality json to zone

Revision ID: 40052d4c34f8
Revises: 708bdfcb9b0f
Create Date: 2026-09-09 18:16:21.796956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '40052d4c34f8'
down_revision: Union[str, Sequence[str], None] = '708bdfcb9b0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add nullable first so existing zone rows don't violate NOT NULL,
    # backfill an empty object, then tighten to NOT NULL.
    op.add_column('zone', sa.Column('data_quality_json', sa.JSON(), nullable=True))
    op.execute("UPDATE zone SET data_quality_json = '{}'::json WHERE data_quality_json IS NULL")
    op.alter_column('zone', 'data_quality_json', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('zone', 'data_quality_json')

"""add real coordinates to zone and shelter

Revision ID: 306ebfdd422a
Revises: 40052d4c34f8
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '306ebfdd422a'
down_revision: Union[str, Sequence[str], None] = '40052d4c34f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('zone', sa.Column('center_lat', sa.Float(), nullable=True))
    op.add_column('zone', sa.Column('center_lon', sa.Float(), nullable=True))
    op.add_column('shelter', sa.Column('lat', sa.Float(), nullable=True))
    op.add_column('shelter', sa.Column('lon', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('shelter', 'lon')
    op.drop_column('shelter', 'lat')
    op.drop_column('zone', 'center_lon')
    op.drop_column('zone', 'center_lat')

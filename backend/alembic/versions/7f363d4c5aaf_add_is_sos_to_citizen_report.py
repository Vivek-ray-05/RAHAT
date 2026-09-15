"""add is_sos to citizen_report

Revision ID: 7f363d4c5aaf
Revises: 306ebfdd422a
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '7f363d4c5aaf'
down_revision: Union[str, Sequence[str], None] = '306ebfdd422a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('citizenreport', sa.Column('is_sos', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('citizenreport', 'is_sos')

"""add_metrics_to_chat_messages

Revision ID: a1b2c3d4e5f6
Revises: 6a0872ef034f
Create Date: 2026-02-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6a0872ef034f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add metrics column to chat_messages table."""
    op.add_column('chat_messages', sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Remove metrics column from chat_messages table."""
    op.drop_column('chat_messages', 'metrics')

"""add chunks tsvector and gin index

Revision ID: cd784ebc62bd
Revises: a1b2c3d4e5f6
Create Date: 2026-02-08 17:00:02.467676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cd784ebc62bd'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) optional normalized text column (recommended)
    op.add_column("chunks", sa.Column("text_norm", sa.Text(), nullable=True))

    # 2) generated tsvector column (stored)
    op.add_column(
        "chunks",
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(text_norm, text))",
                persisted=True,  # => STORED
            ),
            nullable=False,
        ),
    )

    # 3) GIN index
    op.create_index(
        "ix_chunks_tsv_gin",
        "chunks",
        ["tsv"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_tsv_gin", table_name="chunks")
    op.drop_column("chunks", "tsv")
    op.drop_column("chunks", "text_norm")

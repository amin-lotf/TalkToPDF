"""create chats and chat_messages2

Revision ID: 55004a34fc4e
Revises: 089e4eb2fb0f
Create Date: 2026-01-19 19:46:06.421795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '55004a34fc4e'
down_revision: Union[str, Sequence[str], None] = '089e4eb2fb0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0) Create the enum TYPE first (Postgres)
    chat_role_enum = postgresql.ENUM(
        "system",
        "user",
        "assistant",
        name="chat_role_enum",
    )
    chat_role_enum.create(op.get_bind(), checkfirst=True)
    # 1) Create chats (no FK first if you want the circular-safe pattern)
    op.create_table(
        "chats",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chats_owner_id", "chats", ["owner_id"])
    op.create_index("ix_chats_project_id", "chats", ["project_id"])
    op.create_index("ix_chats_owner_project_updated", "chats", ["owner_id", "project_id", "updated_at"])

    # 2) Create chat_messages using the enum TYPE
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("chat_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("role", chat_role_enum, nullable=False),   # <-- use enum type object
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_messages_chat_id", "chat_messages", ["chat_id"])
    op.create_index("ix_chat_messages_chat_created", "chat_messages", ["chat_id", "created_at"])

    # 3) Add FKs after both tables exist (your circular-safe rule)
    op.create_foreign_key(
        "fk_chats_project_id_projects",
        "chats",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_foreign_key(
        "fk_chat_messages_chat_id_chats",
        "chat_messages",
        "chats",
        ["chat_id"],
        ["id"],
        ondelete="CASCADE",
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    # Drop FKs first
    op.drop_constraint("fk_chat_messages_chat_id_chats", "chat_messages", type_="foreignkey")
    op.drop_constraint("fk_chats_project_id_projects", "chats", type_="foreignkey")

    # Drop indexes + tables
    op.drop_index("ix_chat_messages_chat_created", table_name="chat_messages")
    op.drop_index("ix_chat_messages_chat_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chats_owner_project_updated", table_name="chats")
    op.drop_index("ix_chats_project_id", table_name="chats")
    op.drop_index("ix_chats_owner_id", table_name="chats")
    op.drop_table("chats")

    # Finally drop the enum TYPE
    chat_role_enum = postgresql.ENUM(name="chat_role_enum")
    chat_role_enum.drop(op.get_bind(), checkfirst=True)


from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Enum as SAEnum
from sqlalchemy import DateTime, ForeignKey, String, Index, Text, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from talk_to_pdf.backend.app.domain.reply import ChatRole
from talk_to_pdf.backend.app.infrastructure.db import Base


class ChatModel(Base):
    __tablename__ = "chats"

    id: Mapped[UUID] = mapped_column(
        UUID,
        primary_key=True,
        default=uuid4,
    )

    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Optional but useful
    messages: Mapped[list["ChatMessageModel"]] = relationship(
        "ChatMessageModel",
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# Helpful composite index for your main query
Index(
    "ix_chats_owner_project_updated",
    ChatModel.owner_id,
    ChatModel.project_id,
    ChatModel.updated_at.desc(),
)


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    chat_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "chats.id",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped[ChatRole] = mapped_column(
        SAEnum(
            ChatRole,
            name="chat_role_enum",
            native_enum=True,  # PostgreSQL ENUM
            validate_strings=True,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    citations: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    chat: Mapped["ChatModel"] = relationship(
        "ChatModel",
        back_populates="messages",
    )


# Critical for fast pagination
Index(
    "ix_chat_messages_chat_created",
    ChatMessageModel.chat_id,
    ChatMessageModel.created_at,
)
from __future__ import annotations

from dataclasses import dataclass, replace, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from talk_to_pdf.backend.app.domain.common import utcnow
from talk_to_pdf.backend.app.domain.common.enums import ChatRole
from talk_to_pdf.backend.app.domain.reply.value_objects import ChatMessageCitations
from talk_to_pdf.backend.app.domain.reply.metrics import ReplyMetrics


@dataclass(frozen=True, slots=True)
class ChatMessage:
    chat_id: UUID
    role: ChatRole
    content: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)
    citations: ChatMessageCitations | None = None
    metrics: ReplyMetrics | None = None


@dataclass(frozen=True, slots=True)
class Chat:
    owner_id: UUID
    project_id: UUID
    title: str
    id: UUID = field(default_factory=uuid4)
    updated_at: Optional[datetime] = field(default=None)
    created_at: datetime = field(default_factory=utcnow)

    def __post_init__(self):
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", self.created_at)


    def rename(self, *, title: str, updated_at: datetime | None = None) -> "Chat":
        safe_title = (title or "").strip()
        if not safe_title:
            raise ValueError("Chat.title cannot be empty")
        return replace(self, title=safe_title, updated_at=updated_at or utcnow())

    def touch(self, *, updated_at: datetime | None = None) -> "Chat":
        return replace(self, updated_at=updated_at or utcnow())
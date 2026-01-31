from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from talk_to_pdf.backend.app.application.common.dto import ContextPackDTO
from talk_to_pdf.backend.app.domain.common.enums import ChatRole


# -------------------------
# Chats
# -------------------------
@dataclass(frozen=True, slots=True)
class CreateChatInputDTO:
    owner_id: UUID
    project_id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class ChatDTO:
    id: UUID
    owner_id: UUID
    project_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DeleteChatInputDTO:
    owner_id: UUID
    chat_id: UUID


@dataclass(frozen=True, slots=True)
class ListChatsInputDTO:
    owner_id: UUID
    project_id: UUID
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class GetChatInputDTO:
    owner_id: UUID
    chat_id: UUID


@dataclass(frozen=True, slots=True)
class MessageDTO:
    id: UUID
    chat_id: UUID
    role: ChatRole
    content: str
    created_at: datetime
    citations: dict | None = None

@dataclass(frozen=True, slots=True)
class CreateMessageInputDTO:
    owner_id: UUID
    chat_id: UUID
    role: ChatRole
    content: str
    context: ContextPackDTO | None = None
    top_k: int | None = None
    rerank_signature: str | None = None
    prompt_version: str | None = None
    model: str | None = None


@dataclass(frozen=True, slots=True)
class GetChatMessagesInputDTO:
    owner_id: UUID
    chat_id: UUID
    limit: int = 50


# -------------------------
# Reply
# -------------------------
@dataclass(frozen=True, slots=True)
class ReplyInputDTO:
    project_id: UUID
    owner_id: UUID
    chat_id: UUID
    query: str
    top_k: int
    top_n: int
    rerank_timeout_s: float


@dataclass(frozen=True, slots=True)
class ReplyOutputDTO:
    chat_id: UUID
    query: str
    context: ContextPackDTO
    answer: str

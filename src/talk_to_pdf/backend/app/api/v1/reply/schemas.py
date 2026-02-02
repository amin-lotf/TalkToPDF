from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    project_id: UUID
    chat_id: UUID
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    top_n: int = Field(default=5, ge=1, le=20)
    rerank_timeout_s: float = Field(default=0.6, ge=0.0, le=20.0)


class ContextChunkResponse(BaseModel):
    chunk_id: UUID
    chunk_index: int
    text: str
    score: float
    meta: dict[str, Any] | None = None
    citation: dict[str, Any] | None = None


class ContextPackResponse(BaseModel):
    index_id: UUID
    project_id: UUID
    query: str
    embed_signature: str
    metric: str
    chunks: list[ContextChunkResponse]


class ReplyResponse(BaseModel):
    query: str
    answer: str
    context: ContextPackResponse


# -------------------------
# Chat schemas
# -------------------------
class CreateChatRequest(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=200)


class ChatResponse(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID
    title: str
    created_at: str
    updated_at: str


class ListChatsResponse(BaseModel):
    items: list[ChatResponse]


# -------------------------
# Message schemas
# -------------------------
class MessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    role: str
    content: str
    created_at: str
    citations: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None


class ListMessagesResponse(BaseModel):
    items: list[MessageResponse]

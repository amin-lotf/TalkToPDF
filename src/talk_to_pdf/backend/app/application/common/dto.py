from dataclasses import dataclass
from typing import Any
from uuid import UUID

from talk_to_pdf.backend.app.domain.common.enums import VectorMetric
from talk_to_pdf.backend.app.domain.common.value_objects import ChatTurn


@dataclass(frozen=True, slots=True)
class SearchInputDTO:
    owner_id: UUID
    project_id: UUID
    index_id: UUID
    query: str
    message_history: list[ChatTurn]
    top_n: int
    top_k: int
    rerank_timeout_s: float


@dataclass(frozen=True, slots=True)
class ContextChunkDTO:
    chunk_id: UUID
    chunk_index: int
    text: str
    score: float
    meta: dict[str, Any] | None
    citation: dict[str, Any] | None  # keep flexible (page, doc_id, offsets, etc.)
    matched_by: list[int] | None = None


@dataclass(frozen=True, slots=True)
class ContextPackDTO:
    index_id: UUID
    project_id: UUID
    query: str
    embed_signature: str
    metric: VectorMetric
    chunks: list[ContextChunkDTO]
    original_query: str | None = None
    rewritten_query: str | None = None
    rewritten_queries: list[str] | None = None
    rewrite_strategy: str | None = None
    # Query rewriter metrics
    rewrite_prompt_tokens: int = 0
    rewrite_completion_tokens: int = 0
    rewrite_latency: float | None = None

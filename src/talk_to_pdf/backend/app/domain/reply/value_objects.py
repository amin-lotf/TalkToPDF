from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from talk_to_pdf.backend.app.domain.common.enums import VectorMetric


@dataclass(frozen=True, slots=True)
class CitedChunk:
    """Represents a single chunk that was cited in the response."""
    chunk_id: UUID
    score: float | None
    citation: dict[str, Any]  # must include doc_id + page/offsets


@dataclass(frozen=True, slots=True)
class ChatMessageCitations:
    """
    Tracks citations and retrieval metadata for an LLM-generated reply.

    Contains information about:
    - Which index and embedding model were used
    - The retrieval parameters (top_k, reranker, etc.)
    - The actual chunks that were cited with their scores
    - The prompt and model used for generation
    """
    index_id: UUID
    embed_signature: str
    metric: VectorMetric | str
    chunks: list[CitedChunk]
    top_k: int
    rerank_signature: str | None
    prompt_version: str | None
    model: str | None

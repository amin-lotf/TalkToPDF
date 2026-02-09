from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from talk_to_pdf.backend.app.domain.common.value_objects import Vector


BlockKind = Literal[
    "title",
    "section_head",
    "paragraph",
    "equation",
    "table",
    "figure_caption",
    "reference",
    "list_item",
    "footnote",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class Block:
    text: str
    text_norm:str
    meta: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    chunk_index: int
    blocks: list[Block]
    text: str
    text_norm: str
    meta: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingDraft:
    """
    Domain draft for persisting an embedding.
    """
    chunk_id: UUID
    chunk_index: int
    vector: Vector
    meta: dict[str, Any] | None = None  # optional per-embedding metadata


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingRef:
    """
    What you need to identify an embedding row without exposing a DB model.
    """
    id: UUID
    chunk_id: UUID
    chunk_index: int
    embed_signature: str


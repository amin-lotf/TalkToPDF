from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence, List
from uuid import UUID
from talk_to_pdf.backend.app.domain.indexing.value_objects import ChunkDraft, EmbedConfig


class IndexingRunner(Protocol):
    async def enqueue(self, *, index_id: UUID) -> None:
        """Schedule background indexing for this index_id."""
        ...

    async def stop(self, *, index_id: UUID) -> None:
        ...

class TextExtractor(Protocol):
    def extract(self, *, content: bytes) -> str: ...


class Chunker(Protocol):
    def chunk(self, text: str) -> list[ChunkDraft]: ...


class AsyncEmbedder(Protocol):
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]: ...


class EmbedderFactory(Protocol):
    def create(self, cfg: EmbedConfig) -> AsyncEmbedder: ...

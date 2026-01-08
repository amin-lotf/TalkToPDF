from __future__ import annotations

from typing import Protocol
from uuid import UUID

from talk_to_pdf.backend.app.domain.indexing.value_objects import ChunkDraft


class IndexingRunner(Protocol):
    async def enqueue(self, *, index_id: UUID) -> None:
        """Schedule background indexing for this index_id."""
        ...

    async def stop(self, *, index_id: UUID) -> None:
        ...

class TextExtractor(Protocol):
    def extract(self, *, content: bytes) -> str: ...


class Chunker(Protocol):
    def chunk(self, *,text: str) -> list[ChunkDraft]: ...



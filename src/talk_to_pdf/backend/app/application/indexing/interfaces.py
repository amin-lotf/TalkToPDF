from __future__ import annotations

from typing import Protocol
from uuid import UUID

from talk_to_pdf.backend.app.domain.indexing.value_objects import Block, ChunkDraft


class IndexingRunner(Protocol):
    async def enqueue(self, *, index_id: UUID) -> None:
        """Schedule background indexing for this index_id."""
        ...

    async def stop(self, *, index_id: UUID) -> None:
        ...


class PdfToXmlConverter(Protocol):
    def convert(self, *, content: bytes) -> str: ...


class BlockExtractor(Protocol):
    def extract(self, *, xml: str) -> list[Block]: ...


class BlockChunker(Protocol):
    def chunk(self, *, blocks: list[Block]) -> list[ChunkDraft]: ...


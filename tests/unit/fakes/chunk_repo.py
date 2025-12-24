# tests/unit/fakes/chunk_repo.py
from __future__ import annotations

from uuid import UUID
from talk_to_pdf.backend.app.domain.indexing.value_objects import ChunkDraft


class FakeChunkRepository:
    def __init__(self) -> None:
        self._by_index: dict[UUID, list[ChunkDraft]] = {}

    async def bulk_create(self, *, index_id: UUID, chunks: list[ChunkDraft]) -> None:
        self._by_index[index_id] = list(chunks)

    async def list_chunk_ids(self, *, index_id: UUID) -> list[UUID]:
        return []

    async def delete_by_index(self, *, index_id: UUID) -> None:
        self._by_index.pop(index_id, None)

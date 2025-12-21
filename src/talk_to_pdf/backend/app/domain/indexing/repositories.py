from __future__ import annotations

from typing import Protocol
from uuid import UUID

from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig


class DocumentIndexRepository(Protocol):
    async def create_pending(
            self,
            *,
            project_id: UUID,
            document_id: UUID,
            chunker_version: str,
            embed_config: EmbedConfig
    ) -> DocumentIndex:
        ...

    async def get_latest_by_project(self, *, project_id: UUID) -> DocumentIndex | None:
        ...

    async def get_latest_active_by_project_and_signature(self, *, project_id: UUID,
                                                         embed_signature: str) -> DocumentIndex | None:
        ...

    async def get_by_id(self, *, index_id: UUID) -> DocumentIndex | None:
        ...

    async def update_progress(
            self,
            *,
            index_id: UUID,
            status: IndexStatus,
            progress: int,
            message: str | None = None,
            error: str | None = None,
            meta: dict | None = None,
    ) -> None:
        ...

    async def request_cancel(self, *, index_id: UUID) -> None:
        ...

    async def is_cancel_requested(self, *, index_id: UUID) -> bool:
        ...

    async def delete_index_artifacts(self, *, index_id: UUID) -> None:
        ...



class ChunkRepository(Protocol):
    async def bulk_create(self, *, index_id: UUID, chunks: list[tuple[int, str, dict | None]]) -> None: ...
    async def list_chunk_ids(self, *, index_id: UUID) -> list[UUID]: ...
    async def delete_by_index(self, *, index_id: UUID) -> None: ...
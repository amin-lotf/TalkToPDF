from __future__ import annotations

from typing import Protocol
from uuid import UUID

from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.value_objects import ChunkDraft, ChunkEmbeddingDraft
from talk_to_pdf.backend.app.domain.common.value_objects import Chunk, EmbedConfig


class DocumentIndexRepository(Protocol):
    async def create_pending(
            self,
            *,
            project_id: UUID,
            document_id: UUID,
            storage_path: str,
            chunker_version: str,
            embed_config: EmbedConfig
    ) -> DocumentIndex:
        ...

    async def get_latest_by_project(self, *, project_id: UUID) -> DocumentIndex | None:
        ...

    async def get_latest_by_project_and_owner(self, *, project_id: UUID, owner_id: UUID) -> DocumentIndex | None:
        ...

    async def get_latest_ready_by_project_and_owner(self, *, project_id: UUID, owner_id: UUID) -> DocumentIndex | None:
        ...

    async def get_latest_active_by_project_and_signature(self, *, project_id: UUID,
                                                         embed_signature: str) -> DocumentIndex | None:
        ...

    async def get_latest_active_by_project_and_owner_and_signature(self, *, project_id: UUID, owner_id: UUID,
                                                                   embed_signature: str) -> DocumentIndex | None:
        ...

    async def get_by_id(self, *, index_id: UUID) -> DocumentIndex | None:
        ...

    async def get_by_owner_and_id(self, *, owner_id: UUID, index_id: UUID) -> DocumentIndex | None:
        ...

    async def get_by_owner_project_and_id(self, *, owner_id: UUID, project_id:UUID,index_id: UUID) -> DocumentIndex | None:
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
    async def bulk_create(self, *, index_id: UUID, chunks: list[ChunkDraft]) -> None: ...
    async def list_chunk_ids(self, *, index_id: UUID) -> list[UUID]: ...
    async def delete_by_index(self, *, index_id: UUID) -> None: ...
    async def get_many_by_ids_for_index(self, *, index_id: UUID, ids: list[UUID]) -> list[Chunk]:...


class ChunkEmbeddingRepository(Protocol):
    async def bulk_upsert(
        self,
        *,
        index_id: UUID,
        embed_signature: str,
        embeddings: list[ChunkEmbeddingDraft],
    ) -> None:
        """
        Persist embeddings for chunks.
        Upsert semantics are useful because indexing runs can be resumed/retried.
        The uniqueness boundary should be (index_id, chunk_id, embed_signature).
        """
        ...

    async def delete_by_index(
        self,
        *,
        index_id: UUID,
        embed_signature: str | None = None,
    ) -> None:
        """
        Delete embeddings for an index.
        If embed_signature is None: delete all versions for that index.
        """
        ...

    async def exists_for_index(
        self,
        *,
        index_id: UUID,
        embed_signature: str,
    ) -> bool:
        """
        Quick check used for idempotency / skipping work.
        """
        ...





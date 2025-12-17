from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .entities import DocumentIndex
from .enums import IndexStatus


class DocumentIndexRepository(Protocol):
    async def create_pending(
        self,
        *,
        project_id: UUID,
        document_id: UUID,
        chunker_version: str,
        embedder_model: str,
        embedding_dim: int,
    ) -> DocumentIndex:
        ...

    async def get_latest_by_project(self, *, project_id: UUID) -> DocumentIndex | None:
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

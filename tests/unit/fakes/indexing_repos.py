# tests/unit/fakes/index_repo.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig
from talk_to_pdf.backend.app.domain.common import utcnow


class FakeDocumentIndexRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, DocumentIndex] = {}
        self._cancel_requests: set[UUID] = set()

    async def create_pending(
        self,
        *,
        project_id: UUID,
        document_id: UUID,
        chunker_version: str,
        embed_config: EmbedConfig,
    ) -> DocumentIndex:
        idx = DocumentIndex(
            project_id=project_id,
            document_id=document_id,
            chunker_version=chunker_version,
            embed_config=embed_config,
            status=IndexStatus.PENDING,
            progress=0,
            updated_at=utcnow(),
        )
        self._by_id[idx.id] = idx
        return idx

    async def get_latest_by_project(self, *, project_id: UUID) -> Optional[DocumentIndex]:
        candidates = [i for i in self._by_id.values() if i.project_id == project_id]
        return max(candidates, key=lambda i: i.updated_at) if candidates else None

    async def get_latest_active_by_project_and_signature(
        self, *, project_id: UUID, embed_signature: str
    ) -> Optional[DocumentIndex]:
        candidates = [
            i
            for i in self._by_id.values()
            if i.project_id == project_id
            and i.embed_signature == embed_signature
            and i.is_active
        ]
        return max(candidates, key=lambda i: i.updated_at) if candidates else None

    async def get_by_id(self, *, index_id: UUID) -> Optional[DocumentIndex]:
        idx = self._by_id.get(index_id)
        if not idx:
            return None

        if index_id in self._cancel_requests:
            idx = DocumentIndex(
                **{**idx.__dict__, "cancel_requested": True}
            )
            self._by_id[index_id] = idx

        return idx

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
        idx = self._by_id[index_id]
        self._by_id[index_id] = DocumentIndex(
            project_id=idx.project_id,
            document_id=idx.document_id,
            chunker_version=idx.chunker_version,
            embed_config=idx.embed_config,
            status=status,
            progress=progress,
            message=message,
            error=error,
            cancel_requested=idx.cancel_requested,
            updated_at=utcnow(),
            id=idx.id,
        )

    async def request_cancel(self, *, index_id: UUID) -> None:
        self._cancel_requests.add(index_id)

    async def is_cancel_requested(self, *, index_id: UUID) -> bool:
        return index_id in self._cancel_requests

    async def delete_index_artifacts(self, *, index_id: UUID) -> None:
        # domain-wise this deletes chunks/embeddings; here it’s a no-op
        return None

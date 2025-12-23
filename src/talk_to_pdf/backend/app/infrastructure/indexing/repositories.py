from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig, ChunkDraft
from talk_to_pdf.backend.app.infrastructure.indexing.mappers import index_model_to_domain, create_document_index_model, \
    create_chunk_models
from talk_to_pdf.backend.app.infrastructure.db.models.indexing import ChunkModel, DocumentIndexModel





class SqlAlchemyDocumentIndexRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
        self,
        *,
        project_id: UUID,
        document_id: UUID,
        chunker_version: str,
        embed_config: EmbedConfig,
    ) -> DocumentIndex:
        m = create_document_index_model(project_id, document_id, chunker_version, embed_config)
        self._session.add(m)
        await self._session.flush()  # ensures m.id is available before commit
        return index_model_to_domain(m)

    async def get_latest_by_project(self, *, project_id: UUID) -> DocumentIndex | None:
        stmt = (
            select(DocumentIndexModel)
            .where(DocumentIndexModel.project_id == project_id)
            .order_by(desc(DocumentIndexModel.created_at))
            .limit(1)
        )
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return index_model_to_domain(m) if m else None

    async def get_latest_active_by_project_and_signature(self, *, project_id: UUID,embed_signature: str) -> DocumentIndex | None:
        stmt = (
            select(DocumentIndexModel)
            .where(DocumentIndexModel.project_id == project_id)
            .where(DocumentIndexModel.embed_signature == embed_signature)
            .where(DocumentIndexModel.status.in_(IndexStatus.active()))
            .order_by(desc(DocumentIndexModel.created_at))
            .limit(1)
        )
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return index_model_to_domain(m) if m else None

    async def get_by_id(self, *, index_id: UUID) -> DocumentIndex | None:
        stmt = select(DocumentIndexModel).where(DocumentIndexModel.id == index_id)
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return index_model_to_domain(m) if m else None

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
        stmt = (
            update(DocumentIndexModel)
            .where(DocumentIndexModel.id == index_id)
            .values(
                status=status,
                progress=progress,
                message=message,
                error=error,
                meta=meta,
            )
        )
        await self._session.execute(stmt)

    async def request_cancel(self, *, index_id: UUID) -> None:
        stmt = (
            update(DocumentIndexModel)
            .where(DocumentIndexModel.id == index_id)
            .values(cancel_requested=True)
        )
        await self._session.execute(stmt)

    async def is_cancel_requested(self, *, index_id: UUID) -> bool:
        stmt = select(DocumentIndexModel.cancel_requested).where(DocumentIndexModel.id == index_id)
        val = (await self._session.execute(stmt)).scalar_one_or_none()
        return bool(val)

    async def delete_index_artifacts(self, *, index_id: UUID) -> None:
        # If later you add embeddings table, delete those too here.
        await self._session.execute(delete(ChunkModel).where(ChunkModel.index_id == index_id))



class SqlAlchemyChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(
        self,
        *,
        index_id: UUID,
        chunks: list[ChunkDraft],
    ) -> None:
        """
        Insert many chunks for the given index_id.

        chunks format: [(chunk_index, text, meta), ...]
        """
        if not chunks:
            return

        # Build ORM objects
        models=create_chunk_models(index_id,chunks)
        self._session.add_all(models)
        # Flush so they are inserted and IDs are generated (still uncommitted)
        await self._session.flush()

    async def list_chunk_ids(self, *, index_id: UUID) -> list[UUID]:
        """
        Return chunk IDs ordered by chunk_index, so caller can align vectors to chunks.
        """
        stmt = (
            select(ChunkModel.id)
            .where(ChunkModel.index_id == index_id)
            .order_by(ChunkModel.chunk_index.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(rows)

    async def list_chunks_for_index(self, *, index_id: UUID) -> list[ChunkModel]:
        """
        Optional convenience method: get full chunk rows ordered by chunk_index.
        Useful for debugging / retrieval pipelines.
        """
        stmt = (
            select(ChunkModel)
            .where(ChunkModel.index_id == index_id)
            .order_by(ChunkModel.chunk_index.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def delete_by_index(self, *, index_id: UUID) -> None:
        """
        Delete all chunks for a given index_id.
        Note: ON DELETE CASCADE also handles deletes when index is deleted,
        but this is useful for "cancel requested" cleanup.
        """
        stmt = delete(ChunkModel).where(ChunkModel.index_id == index_id)
        await self._session.execute(stmt)

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, desc, select, update, exists, func
from sqlalchemy.dialects.postgresql import insert

from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.common.enums import VectorMetric, MatchSource
from talk_to_pdf.backend.app.domain.indexing.value_objects import ChunkDraft, ChunkEmbeddingDraft
from talk_to_pdf.backend.app.domain.common.value_objects import Vector, Chunk, EmbedConfig
from talk_to_pdf.backend.app.domain.retrieval.value_objects import ChunkMatch
from talk_to_pdf.backend.app.infrastructure.db.models import ProjectModel
from talk_to_pdf.backend.app.infrastructure.indexing.mappers import index_model_to_domain, create_document_index_model, \
    create_chunk_models, embedding_drafts_to_insert_rows, rows_to_chunk_matches, chunk_model_to_domain
from talk_to_pdf.backend.app.infrastructure.db.models.indexing import ChunkModel, DocumentIndexModel, \
    ChunkEmbeddingModel


class SqlAlchemyDocumentIndexRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
            self,
            *,
            project_id: UUID,
            document_id: UUID,
            storage_path: str,
            chunker_version: str,
            embed_config: EmbedConfig,
    ) -> DocumentIndex:
        m = create_document_index_model(
            project_id=project_id,
            document_id=document_id,
            storage_path=storage_path,
            chunker_version=chunker_version,
            embed_config=embed_config
        )
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

    async def get_latest_by_project_and_owner(self, *, project_id: UUID, owner_id: UUID) -> DocumentIndex | None:
        stmt = (
            select(DocumentIndexModel)
            .join(ProjectModel, ProjectModel.id == DocumentIndexModel.project_id)
            .where(DocumentIndexModel.project_id == project_id, ProjectModel.owner_id == owner_id)
            .order_by(desc(DocumentIndexModel.created_at))
            .limit(1)
        )
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return index_model_to_domain(m) if m else None

    async def get_latest_ready_by_project_and_owner(self, *, project_id: UUID, owner_id: UUID) -> DocumentIndex | None:
        stmt = (
            select(DocumentIndexModel)
            .join(ProjectModel, ProjectModel.id == DocumentIndexModel.project_id)
            .where(DocumentIndexModel.project_id == project_id, ProjectModel.owner_id == owner_id)
            .where(DocumentIndexModel.status == IndexStatus.READY)
            .order_by(desc(DocumentIndexModel.created_at))
            .limit(1)
        )
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return index_model_to_domain(m) if m else None

    async def get_latest_ready_by_project_and_owner_and_signature(self, *, project_id: UUID, owner_id: UUID,
                                                                  embed_signature: str) -> DocumentIndex | None:
        stmt = (
            select(DocumentIndexModel)
            .join(ProjectModel, ProjectModel.id == DocumentIndexModel.project_id)
            .where(DocumentIndexModel.project_id == project_id, ProjectModel.owner_id == owner_id)
            .where(DocumentIndexModel.embed_signature == embed_signature)
            .where(DocumentIndexModel.status == IndexStatus.READY)
            .order_by(desc(DocumentIndexModel.created_at))
            .limit(1)
        )
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return index_model_to_domain(m) if m else None

    async def get_latest_active_by_project_and_signature(self, *, project_id: UUID,
                                                         embed_signature: str) -> DocumentIndex | None:
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

    async def get_latest_active_by_project_and_owner_and_signature(self, *, project_id: UUID,owner_id: UUID,
                                                         embed_signature: str) -> DocumentIndex | None:
        stmt = (
            select(DocumentIndexModel)
            .join(ProjectModel, ProjectModel.id == DocumentIndexModel.project_id)
            .where(DocumentIndexModel.project_id == project_id)
            .where(ProjectModel.owner_id == owner_id)
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

    async def get_by_owner_and_id(self, *, owner_id: UUID, index_id: UUID) -> DocumentIndex | None:
        stmt = (
            select(DocumentIndexModel)
            .join(ProjectModel, ProjectModel.id == DocumentIndexModel.project_id)
            .where(
                DocumentIndexModel.id == index_id,
                ProjectModel.owner_id == owner_id,
            )
        )
        model = await self._session.scalar(stmt)
        return index_model_to_domain(model) if model else None

    async def get_by_owner_project_and_id(self, *, owner_id: UUID, project_id:UUID,index_id: UUID) -> DocumentIndex | None:
        stmt = (
            select(DocumentIndexModel)
            .join(ProjectModel, ProjectModel.id == DocumentIndexModel.project_id)
            .where(
                DocumentIndexModel.id == index_id,
                ProjectModel.id == project_id,
                ProjectModel.owner_id == owner_id,
            )
        )
        model = await self._session.scalar(stmt)
        return index_model_to_domain(model) if model else None

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
        models = create_chunk_models(index_id, chunks)
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

    async def get_many_by_ids_for_index(self, *, index_id: UUID, ids: list[UUID]) -> list[Chunk]:
        stmt = select(ChunkModel).where(
            ChunkModel.index_id == index_id,
            ChunkModel.id.in_(ids),
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [chunk_model_to_domain(m) for m in rows]

class SqlAlchemyChunkVectorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_upsert(
        self,
        *,
        index_id: UUID,
        embed_signature: str,
        embeddings: list[ChunkEmbeddingDraft],
    ) -> None:
        """
        Upsert embeddings for (index_id, chunk_id, embed_signature).

        This is resilient to retries: if the worker restarts mid-run,
        re-running bulk_upsert overwrites existing embeddings.
        """
        if not embeddings:
            return

        # Optional sanity: all vectors should have same dim
        # (We don't hard-fail on mixed dims unless you want to.)
        dim0 = embeddings[0].vector.dim
        if any(e.vector.dim != dim0 for e in embeddings):
            raise ValueError("All embeddings in a bulk_upsert must have the same vector dimension")

        rows = embedding_drafts_to_insert_rows(
            index_id=index_id,
            embed_signature=embed_signature,
            embeddings=embeddings,
        )

        stmt = insert(ChunkEmbeddingModel).values(rows)

        # Requires a UNIQUE constraint on (index_id, chunk_id, embed_signature)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                ChunkEmbeddingModel.index_id,
                ChunkEmbeddingModel.chunk_id,
                ChunkEmbeddingModel.embed_signature,
            ],
            set_={
                "chunk_index": stmt.excluded.chunk_index,
                "embedding": stmt.excluded.embedding,
                # If you want updated timestamps:
                # "updated_at": func.now(),
            },
        )

        await self._session.execute(stmt)
        await self._session.flush()

    async def delete_by_index(
        self,
        *,
        index_id: UUID,
        embed_signature: str | None = None,
    ) -> None:
        """
        Delete embeddings for an index.
        If embed_signature is provided: delete only that embedding space/version.
        """
        stmt = delete(ChunkEmbeddingModel).where(ChunkEmbeddingModel.index_id == index_id)
        if embed_signature is not None:
            stmt = stmt.where(ChunkEmbeddingModel.embed_signature == embed_signature)
        await self._session.execute(stmt)

    async def exists_for_index(
        self,
        *,
        index_id: UUID,
        embed_signature: str,
    ) -> bool:
        """
        True if there is at least one embedding row for this index+signature.
        """
        stmt = select(
            exists()
            .where(ChunkEmbeddingModel.index_id == index_id)
            .where(ChunkEmbeddingModel.embed_signature == embed_signature)
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def similarity_search(
        self,
        *,
        query: Vector,
        top_k: int,
        embed_signature: str,
        index_id: UUID,
        metric: VectorMetric = VectorMetric.COSINE,
    ) -> list[ChunkMatch]:
        """
        Return top_k matches within a single index_id (your choice).

        Score semantics:
          - COSINE/IP: higher score is better
          - L2: lower distance is better, we return score = -distance
        """
        if top_k <= 0:
            return []

        # pgvector comparator operators differ by metric:
        # - cosine distance: embedding.cosine_distance(vec)
        # - l2 distance: embedding.l2_distance(vec)
        # - inner product: embedding.max_inner_product(vec)  (naming varies by pgvector sqlalchemy version)
        #
        # We'll implement in a way that is compatible with common pgvector.sqlalchemy comparators:
        vec = list(query.values)

        emb_col = ChunkEmbeddingModel.embedding

        if metric == VectorMetric.COSINE:
            distance_expr = emb_col.cosine_distance(vec)
            order_expr = distance_expr.asc()
            score_expr = (1.0 - distance_expr).label("score")  # cosine similarity
        elif metric == VectorMetric.L2:
            distance_expr = emb_col.l2_distance(vec)
            order_expr = distance_expr.asc()
            score_expr = (-distance_expr).label("score")  # or transform to 1/(1+d)
        elif metric == VectorMetric.INNER_PRODUCT:
            # pgvector's inner product operator is distance-like in many bindings;
            # keep your -distance approach if you're ordering ASC.
            distance_expr = emb_col.max_inner_product(vec)
            order_expr = distance_expr.asc()
            score_expr = (-distance_expr).label("score")
        else:
            raise ValueError(f"Unsupported metric: {metric}")

        stmt = (
            select(
                ChunkEmbeddingModel.chunk_id,
                ChunkEmbeddingModel.chunk_index,
                score_expr,
            )
            .where(ChunkEmbeddingModel.index_id == index_id)
            .where(ChunkEmbeddingModel.embed_signature == embed_signature)
            .order_by(order_expr)
            .limit(top_k)
        )

        rows = (await self._session.execute(stmt)).all()
        return rows_to_chunk_matches(rows, source=MatchSource.VECTOR)

    async def fts_search(
        self,
        *,
        index_id: UUID,
        query: str,
        top_k: int,
        config: str = "english",
    ) -> list[ChunkMatch]:
        """
        Lexical search using Postgres full text search.
        - Uses websearch_to_tsquery for friendly syntax and good recall.
        - Returns ts_rank_cd scores (higher is better).
        """
        if top_k <= 0:
            return []
        q = (query or "").strip()
        if not q:
            return []

        # websearch_to_tsquery handles terms like: isac, "soft actor-critic", Zhang, etc.
        tsquery = func.websearch_to_tsquery(config, q)

        rank = func.ts_rank_cd(ChunkModel.tsv, tsquery).label("score")

        stmt = (
            select(
                ChunkModel.id.label("chunk_id"),
                ChunkModel.chunk_index,
                rank,
            )
            .where(ChunkModel.index_id == index_id)
            .where(ChunkModel.tsv.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(top_k)
        )

        rows = (await self._session.execute(stmt)).all()
        return rows_to_chunk_matches(rows, source=MatchSource.FTS)
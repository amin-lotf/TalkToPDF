from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select

from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus, VectorMetric
from talk_to_pdf.backend.app.domain.indexing.value_objects import (
    ChunkEmbeddingDraft,
    Vector,
    EmbedConfig,
)
from talk_to_pdf.backend.app.infrastructure.db.models import (
    ChunkEmbeddingModel,
    ChunkModel,
    DocumentIndexModel,
)
from talk_to_pdf.backend.app.infrastructure.indexing.repositories import SqlAlchemyChunkEmbeddingRepository

pytestmark = pytest.mark.asyncio


@pytest.fixture
def repo(session) -> SqlAlchemyChunkEmbeddingRepository:
    return SqlAlchemyChunkEmbeddingRepository(session)


def _vec(values: list[float]) -> Vector:
    # Your Vector VO appears to carry (values, dim)
    return Vector(values=tuple(values), dim=len(values))


async def _seed_index(session, *, embed_signature: str = "sig:v1") -> UUID:
    cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=32, dimensions=1536)
    idx = DocumentIndexModel(
        project_id=uuid4(),
        document_id=uuid4(),
        storage_path="/fake/path.pdf",
        status=IndexStatus.PENDING,
        progress=0,
        message="Queued",
        error=None,
        cancel_requested=False,
        chunker_version="v1",
        meta=None,
        embed_config=cfg.to_dict(),
        embed_signature=embed_signature,
    )
    session.add(idx)
    await session.flush()
    return idx.id


async def _seed_chunks(session, *, index_id: UUID, n: int) -> list[ChunkModel]:
    chunks: list[ChunkModel] = []
    for i in range(n):
        chunks.append(
            ChunkModel(
                index_id=index_id,
                chunk_index=i,
                text=f"chunk-{i}",
                meta=None,
            )
        )
    session.add_all(chunks)
    await session.flush()
    return chunks


async def _count_embeddings(session, *, index_id: UUID, sig: str | None = None) -> int:
    stmt = select(func.count()).select_from(ChunkEmbeddingModel).where(ChunkEmbeddingModel.index_id == index_id)
    if sig is not None:
        stmt = stmt.where(ChunkEmbeddingModel.embed_signature == sig)
    return int((await session.execute(stmt)).scalar_one())


async def _get_embedding_row(
    session,
    *,
    index_id: UUID,
    chunk_id: UUID,
    sig: str,
) -> ChunkEmbeddingModel:
    stmt = (
        select(ChunkEmbeddingModel)
        .where(ChunkEmbeddingModel.index_id == index_id)
        .where(ChunkEmbeddingModel.chunk_id == chunk_id)
        .where(ChunkEmbeddingModel.embed_signature == sig)
    )
    return (await session.execute(stmt)).scalar_one()


async def test_bulk_upsert_noop_on_empty_list(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    index_id = await _seed_index(session)
    await _seed_chunks(session, index_id=index_id, n=2)

    await repo.bulk_upsert(index_id=index_id, embed_signature="sig:v1", embeddings=[])
    await session.commit()

    assert await _count_embeddings(session, index_id=index_id) == 0


async def test_bulk_upsert_rejects_mixed_dims(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    index_id = await _seed_index(session)
    chunks = await _seed_chunks(session, index_id=index_id, n=2)

    drafts = [
        ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([1.0, 0.0])),
        ChunkEmbeddingDraft(chunk_id=chunks[1].id, chunk_index=1, vector=_vec([1.0, 0.0, 0.0])),
    ]

    with pytest.raises(ValueError, match="same vector dimension"):
        await repo.bulk_upsert(index_id=index_id, embed_signature="sig:v1", embeddings=drafts)


async def test_bulk_upsert_inserts_rows_and_flushes(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    index_id = await _seed_index(session)
    chunks = await _seed_chunks(session, index_id=index_id, n=2)

    drafts = [
        ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([1.0, 0.0])),
        ChunkEmbeddingDraft(chunk_id=chunks[1].id, chunk_index=1, vector=_vec([0.0, 1.0])),
    ]

    await repo.bulk_upsert(index_id=index_id, embed_signature="sig:v1", embeddings=drafts)

    # flush in repo means rows exist before commit (within current tx)
    assert await _count_embeddings(session, index_id=index_id, sig="sig:v1") == 2

    await session.commit()
    assert await _count_embeddings(session, index_id=index_id, sig="sig:v1") == 2


async def test_bulk_upsert_is_retry_safe_overwrites_on_conflict(
    session,
    repo: SqlAlchemyChunkEmbeddingRepository,
) -> None:
    index_id = await _seed_index(session)
    chunks = await _seed_chunks(session, index_id=index_id, n=2)

    sig = "sig:v1"

    await repo.bulk_upsert(
        index_id=index_id,
        embed_signature=sig,
        embeddings=[
            ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([1.0, 0.0])),
            ChunkEmbeddingDraft(chunk_id=chunks[1].id, chunk_index=1, vector=_vec([0.0, 1.0])),
        ],
    )
    await session.commit()

    assert await _count_embeddings(session, index_id=index_id, sig=sig) == 2

    # re-run with SAME unique key (index_id, chunk_id, sig) but different values -> must update
    await repo.bulk_upsert(
        index_id=index_id,
        embed_signature=sig,
        embeddings=[
            ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=999, vector=_vec([0.25, 0.75])),
        ],
    )
    await session.commit()

    assert await _count_embeddings(session, index_id=index_id, sig=sig) == 2

    row = await _get_embedding_row(session, index_id=index_id, chunk_id=chunks[0].id, sig=sig)
    assert row.chunk_index == 999
    assert list(row.embedding) == [0.25, 0.75]


async def test_exists_for_index(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    index_id = await _seed_index(session)
    chunks = await _seed_chunks(session, index_id=index_id, n=1)
    sig = "sig:v1"

    assert await repo.exists_for_index(index_id=index_id, embed_signature=sig) is False

    await repo.bulk_upsert(
        index_id=index_id,
        embed_signature=sig,
        embeddings=[ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([1.0, 0.0]))],
    )
    await session.commit()

    assert await repo.exists_for_index(index_id=index_id, embed_signature=sig) is True


async def test_delete_by_index_deletes_all_or_signature_scoped(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    index_id = await _seed_index(session)
    chunks = await _seed_chunks(session, index_id=index_id, n=2)

    sig_a = "sig:A"
    sig_b = "sig:B"

    await repo.bulk_upsert(
        index_id=index_id,
        embed_signature=sig_a,
        embeddings=[
            ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([1.0, 0.0])),
            ChunkEmbeddingDraft(chunk_id=chunks[1].id, chunk_index=1, vector=_vec([0.0, 1.0])),
        ],
    )
    await repo.bulk_upsert(
        index_id=index_id,
        embed_signature=sig_b,
        embeddings=[
            ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([0.5, 0.5])),
        ],
    )
    await session.commit()

    assert await _count_embeddings(session, index_id=index_id) == 3

    # delete only sig_a
    await repo.delete_by_index(index_id=index_id, embed_signature=sig_a)
    await session.commit()

    assert await _count_embeddings(session, index_id=index_id, sig=sig_a) == 0
    assert await _count_embeddings(session, index_id=index_id, sig=sig_b) == 1

    # delete remaining for index
    await repo.delete_by_index(index_id=index_id, embed_signature=None)
    await session.commit()

    assert await _count_embeddings(session, index_id=index_id) == 0


async def test_similarity_search_topk_le_zero_returns_empty(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    index_id = await _seed_index(session)
    await _seed_chunks(session, index_id=index_id, n=1)

    out = await repo.similarity_search(
        query=_vec([1.0, 0.0]),
        top_k=0,
        embed_signature="sig:v1",
        index_id=index_id,
        metric=VectorMetric.COSINE,
    )
    assert out == []


async def test_similarity_search_cosine_ranks_expected(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    index_id = await _seed_index(session)
    chunks = await _seed_chunks(session, index_id=index_id, n=3)
    sig = "sig:v1"

    # query [1,0] should rank:
    # [1,0] best, then [0,1], then [-1,0]
    await repo.bulk_upsert(
        index_id=index_id,
        embed_signature=sig,
        embeddings=[
            ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([1.0, 0.0])),
            ChunkEmbeddingDraft(chunk_id=chunks[1].id, chunk_index=1, vector=_vec([0.0, 1.0])),
            ChunkEmbeddingDraft(chunk_id=chunks[2].id, chunk_index=2, vector=_vec([-1.0, 0.0])),
        ],
    )
    await session.commit()

    res = await repo.similarity_search(
        query=_vec([1.0, 0.0]),
        top_k=3,
        embed_signature=sig,
        index_id=index_id,
        metric=VectorMetric.COSINE,
    )

    assert [m.chunk_id for m in res] == [chunks[0].id, chunks[1].id, chunks[2].id]
    assert res[0].score >= res[1].score >= res[2].score


async def test_similarity_search_l2_ranks_expected(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    index_id = await _seed_index(session)
    chunks = await _seed_chunks(session, index_id=index_id, n=3)
    sig = "sig:v1"

    # origin ranks [0,0] then [1,0] then [2,0]
    await repo.bulk_upsert(
        index_id=index_id,
        embed_signature=sig,
        embeddings=[
            ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([0.0, 0.0])),
            ChunkEmbeddingDraft(chunk_id=chunks[1].id, chunk_index=1, vector=_vec([1.0, 0.0])),
            ChunkEmbeddingDraft(chunk_id=chunks[2].id, chunk_index=2, vector=_vec([2.0, 0.0])),
        ],
    )
    await session.commit()

    res = await repo.similarity_search(
        query=_vec([0.0, 0.0]),
        top_k=3,
        embed_signature=sig,
        index_id=index_id,
        metric=VectorMetric.L2,
    )

    assert [m.chunk_id for m in res] == [chunks[0].id, chunks[1].id, chunks[2].id]
    assert res[0].score >= res[1].score >= res[2].score


async def test_similarity_search_inner_product_orders_by_largest_score_or_skips(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    # Your repo uses emb_col.max_inner_product(vec) — depending on pgvector/sqlalchemy version,
    # the comparator might be named differently. If it's missing, skip.
    if not hasattr(ChunkEmbeddingModel.embedding, "max_inner_product"):
        pytest.skip("pgvector comparator does not expose max_inner_product in this environment")

    index_id = await _seed_index(session)
    chunks = await _seed_chunks(session, index_id=index_id, n=3)
    sig = "sig:v1"

    await repo.bulk_upsert(
        index_id=index_id,
        embed_signature=sig,
        embeddings=[
            ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([1.0, 0.0])),    # dot 1
            ChunkEmbeddingDraft(chunk_id=chunks[1].id, chunk_index=1, vector=_vec([0.0, 1.0])),    # dot 0
            ChunkEmbeddingDraft(chunk_id=chunks[2].id, chunk_index=2, vector=_vec([-1.0, 0.0])),   # dot -1
        ],
    )
    await session.commit()

    res = await repo.similarity_search(
        query=_vec([1.0, 0.0]),
        top_k=3,
        embed_signature=sig,
        index_id=index_id,
        metric=VectorMetric.INNER_PRODUCT,
    )

    assert [m.chunk_id for m in res] == [chunks[0].id, chunks[1].id, chunks[2].id]
    assert res[0].score >= res[1].score >= res[2].score


async def test_cascade_delete_index_removes_chunk_embeddings(session, repo: SqlAlchemyChunkEmbeddingRepository) -> None:
    # This is a real integration test of your FK ondelete="CASCADE"
    index_id = await _seed_index(session)
    chunks = await _seed_chunks(session, index_id=index_id, n=2)
    sig = "sig:v1"

    await repo.bulk_upsert(
        index_id=index_id,
        embed_signature=sig,
        embeddings=[
            ChunkEmbeddingDraft(chunk_id=chunks[0].id, chunk_index=0, vector=_vec([1.0, 0.0])),
            ChunkEmbeddingDraft(chunk_id=chunks[1].id, chunk_index=1, vector=_vec([0.0, 1.0])),
        ],
    )
    await session.commit()

    assert await _count_embeddings(session, index_id=index_id) == 2

    # Delete the index row -> cascades to chunks and chunk_embeddings (because both have FK ondelete=CASCADE)
    await session.execute(delete(DocumentIndexModel).where(DocumentIndexModel.id == index_id))
    await session.commit()

    # embeddings should be gone
    stmt = select(func.count()).select_from(ChunkEmbeddingModel).where(ChunkEmbeddingModel.index_id == index_id)
    assert int((await session.execute(stmt)).scalar_one()) == 0

# tests/integration/infrastructure/indexing/test_document_index_repository.py
from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.infrastructure.db.models import DocumentIndexModel, ChunkModel
from talk_to_pdf.backend.app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from talk_to_pdf.backend.app.infrastructure.indexing.repositories import SqlAlchemyDocumentIndexRepository

pytestmark = pytest.mark.asyncio


def _any_active_status() -> IndexStatus:
    active = IndexStatus.active()
    assert active, "IndexStatus.active() returned empty; test needs at least one active status."
    return active[0]


@pytest.fixture
def repo(session: AsyncSession) -> SqlAlchemyDocumentIndexRepository:
    return SqlAlchemyDocumentIndexRepository(session)


@pytest.fixture
def embed_config() -> EmbedConfig:
    return EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=32, dimensions=1536)


async def _set_created_at(session: AsyncSession, *, index_id: UUID, delta: timedelta) -> None:
    await session.execute(
        update(DocumentIndexModel)
        .where(DocumentIndexModel.id == index_id)
        .values(created_at=func.now() + delta)
    )


async def _count_chunks(session: AsyncSession, *, index_id: UUID) -> int:
    stmt = select(func.count()).select_from(ChunkModel).where(ChunkModel.index_id == index_id)
    return int((await session.execute(stmt)).scalar_one())


async def test_create_pending_flushes_id_and_persists_fields(
    session: AsyncSession,
    repo: SqlAlchemyDocumentIndexRepository,
    embed_config: EmbedConfig,
) -> None:
    project_id = uuid4()
    document_id = uuid4()

    idx = await repo.create_pending(
        project_id=project_id,
        document_id=document_id,
        chunker_version="v1",
        embed_config=embed_config,
    )

    # Important: create_pending does a flush -> id must exist before commit.
    assert isinstance(idx.id, UUID)

    # Persist and verify round-trip through DB.
    await session.commit()
    got = await repo.get_by_id(index_id=idx.id)

    assert got is not None
    assert got.id == idx.id
    assert got.project_id == project_id
    assert got.document_id == document_id
    assert got.chunker_version == "v1"
    assert got.status == IndexStatus.PENDING
    assert got.progress == 0
    assert got.cancel_requested is False

    # Load-bearing: embed_signature is derived from EmbedConfig.signature()
    assert got.embed_signature == embed_config.signature()


async def test_get_latest_by_project_returns_most_recent(
    session: AsyncSession,
    repo: SqlAlchemyDocumentIndexRepository,
    embed_config: EmbedConfig,
) -> None:
    project_id = uuid4()

    older = await repo.create_pending(
        project_id=project_id, document_id=uuid4(), chunker_version="v1", embed_config=embed_config
    )
    newer = await repo.create_pending(
        project_id=project_id, document_id=uuid4(), chunker_version="v1", embed_config=embed_config
    )

    # Make ordering deterministic.
    await _set_created_at(session, index_id=older.id, delta=timedelta(days=-1))
    await _set_created_at(session, index_id=newer.id, delta=timedelta(days=+1))
    await session.commit()

    got = await repo.get_latest_by_project(project_id=project_id)
    assert got is not None
    assert got.id == newer.id


async def test_get_latest_active_by_project_and_signature_filters_by_signature_and_active_status(
    session: AsyncSession,
    repo: SqlAlchemyDocumentIndexRepository,
    embed_config: EmbedConfig,
) -> None:
    project_id = uuid4()

    # Same project, same signature, but different statuses and created_at.
    a1 = await repo.create_pending(
        project_id=project_id, document_id=uuid4(), chunker_version="v1", embed_config=embed_config
    )
    a2 = await repo.create_pending(
        project_id=project_id, document_id=uuid4(), chunker_version="v1", embed_config=embed_config
    )

    # Different signature (different embed_config).
    other_config = EmbedConfig(provider="openai", model="text-embedding-3-large", batch_size=16, dimensions=3072)
    b1 = await repo.create_pending(
        project_id=project_id, document_id=uuid4(), chunker_version="v1", embed_config=other_config
    )

    active_status = _any_active_status()

    # Make only a2 active; keep a1 pending (non-active). Make b1 active but signature mismatch.
    await repo.update_progress(index_id=a2.id, status=active_status, progress=80, message="running")
    await repo.update_progress(index_id=b1.id, status=active_status, progress=80, message="running")

    # Ensure a2 is the latest among matching signature+active.
    await _set_created_at(session, index_id=a1.id, delta=timedelta(days=-2))
    await _set_created_at(session, index_id=a2.id, delta=timedelta(days=+2))
    await _set_created_at(session, index_id=b1.id, delta=timedelta(days=+10))
    await session.commit()

    got = await repo.get_latest_active_by_project_and_signature(
        project_id=project_id,
        embed_signature=embed_config.signature(),
    )
    assert got is not None
    assert got.id == a2.id
    assert got.embed_signature == embed_config.signature()
    assert got.status == active_status


async def test_update_progress_updates_fields_including_meta_message_error(
    session: AsyncSession,
    repo: SqlAlchemyDocumentIndexRepository,
    embed_config: EmbedConfig,
) -> None:
    idx = await repo.create_pending(
        project_id=uuid4(), document_id=uuid4(), chunker_version="v1", embed_config=embed_config
    )
    await session.commit()

    meta = {"chunks": 12, "note": "halfway"}
    active_status = _any_active_status()

    await repo.update_progress(
        index_id=idx.id,
        status=active_status,
        progress=55,
        message="processing",
        error=None,
        meta=meta,
    )
    await session.commit()

    got = await repo.get_by_id(index_id=idx.id)
    assert got is not None
    assert got.status == active_status
    assert got.progress == 55
    assert got.message == "processing"
    assert got.error is None

    # Meta is stored on the model; verify at DB level since domain entity may or may not expose it.
    stmt = select(DocumentIndexModel.meta).where(DocumentIndexModel.id == idx.id)
    meta_in_db = (await session.execute(stmt)).scalar_one()
    assert meta_in_db == meta

    # Also verify error updates.
    await repo.update_progress(
        index_id=idx.id,
        status=IndexStatus.FAILED,
        progress=100,
        message="failed",
        error="boom",
        meta={"chunks": 12, "note": "failed"},
    )
    await session.commit()

    got2 = await repo.get_by_id(index_id=idx.id)
    assert got2 is not None
    assert got2.status == IndexStatus.FAILED
    assert got2.progress == 100
    assert got2.error == "boom"


async def test_request_cancel_and_is_cancel_requested(
    session: AsyncSession,
    repo: SqlAlchemyDocumentIndexRepository,
    embed_config: EmbedConfig,
) -> None:
    idx = await repo.create_pending(
        project_id=uuid4(), document_id=uuid4(), chunker_version="v1", embed_config=embed_config
    )
    await session.commit()

    assert await repo.is_cancel_requested(index_id=idx.id) is False

    await repo.request_cancel(index_id=idx.id)
    await session.commit()

    assert await repo.is_cancel_requested(index_id=idx.id) is True


async def test_delete_index_artifacts_deletes_chunks_only_for_that_index(
    session: AsyncSession,
    repo: SqlAlchemyDocumentIndexRepository,
    embed_config: EmbedConfig,
) -> None:
    idx1 = await repo.create_pending(
        project_id=uuid4(), document_id=uuid4(), chunker_version="v1", embed_config=embed_config
    )
    idx2 = await repo.create_pending(
        project_id=uuid4(), document_id=uuid4(), chunker_version="v1", embed_config=embed_config
    )
    await session.commit()

    # ChunkModel fields are: id (default), index_id, chunk_index, text, meta (optional)
    session.add_all(
        [
            ChunkModel(index_id=idx1.id, chunk_index=0, text="a", meta={"p": 1}),
            ChunkModel(index_id=idx1.id, chunk_index=1, text="b", meta=None),
            ChunkModel(index_id=idx2.id, chunk_index=0, text="x", meta=None),
        ]
    )
    await session.commit()

    assert await _count_chunks(session, index_id=idx1.id) == 2
    assert await _count_chunks(session, index_id=idx2.id) == 1

    await repo.delete_index_artifacts(index_id=idx1.id)
    await session.commit()

    assert await _count_chunks(session, index_id=idx1.id) == 0
    assert await _count_chunks(session, index_id=idx2.id) == 1



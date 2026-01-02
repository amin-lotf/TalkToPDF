from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, func

from talk_to_pdf.backend.app.core import settings
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig, Vector
from talk_to_pdf.backend.app.infrastructure.db.models import DocumentIndexModel, ChunkEmbeddingModel
from talk_to_pdf.backend.app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO
from talk_to_pdf.backend.app.application.projects.use_cases.create_project import CreateProjectUseCase

from talk_to_pdf.backend.app.application.indexing.dto import StartIndexingInputDTO
from talk_to_pdf.backend.app.application.indexing.use_cases.start_indexing import StartIndexingUseCase
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage
from talk_to_pdf.backend.app.infrastructure.indexing.embedders.factory_openai_langchain import OpenAIEmbedderFactory

from talk_to_pdf.backend.app.infrastructure.indexing.extractors.pypdf_extractor import PyPDFTextExtractor
from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.simple_char_chunker import SimpleCharChunker
from talk_to_pdf.backend.app.infrastructure.indexing.service import IndexingWorkerService, WorkerDeps


pytestmark = pytest.mark.asyncio


# ---------------------------
# Helpers
# ---------------------------




@dataclass
class NoopRunner:
    async def enqueue(self, *, index_id):
        return


class DummyEmbedderFactory:
    def create(self, embed_cfg):
        raise RuntimeError("Embedding should not be reached in extract-only test.")


# ---------------------------
# Test
# ---------------------------

async def test_worker_extract_prints_preview_lines(session,uow,pdf_bytes, monkeypatch, capsys, tmp_path: Path):
    """
    End-to-end through:
      - CreateProjectUseCase (persists project + doc)
      - StartIndexingUseCase (creates DocumentIndex row)
      - IndexingWorkerService.run() (extracts and prints first lines)
    """


    # Optional: if anything constructs OpenAI factory elsewhere, avoid missing key issues
    if not getattr(settings, "OPENAI_API_KEY", None):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")

    # Build UoW bound to the test session (savepoint-based fixture)

    # 1) Create a real PDF + store it using FilesystemFileStorage (real disk write)
    owner_id = uuid4()


    file_storage = FilesystemFileStorage(base_dir=tmp_path)
    create_project_uc = CreateProjectUseCase(uow=uow, file_storage=file_storage)

    project_out = await create_project_uc.execute(
        CreateProjectInputDTO(
            owner_id=owner_id,
            name="Indexing Extract Test",
            file_bytes=pdf_bytes,
            filename="sample.pdf",
            content_type="application/pdf",
        )
    )

    # 2) Start indexing (runner is stubbed; we’ll run worker directly)
    embed_cfg = EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=16,
        dimensions=1536,
    )

    start_indexing_uc = StartIndexingUseCase(
        uow=uow,
        runner=NoopRunner(),
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    )

    await start_indexing_uc.execute(
        StartIndexingInputDTO(
            owner_id=project_out.owner_id,
            project_id=project_out.id,
            document_id=project_out.primary_document.id,
        )
    )

    # Don’t assume DTO shape for index id — fetch via repo using your idempotency signature rule
    async with uow:
        idx = await uow.index_repo.get_latest_active_by_project_and_signature(
            project_id=project_out.id,
            embed_signature=embed_cfg.signature(),
        )
        assert idx is not None
        index_id = idx.id

    def uow_factory(_session):
        # ignore session; return our in-memory uow
        return SqlAlchemyUnitOfWork(_session)
    # simpler: inline async context manager factory
    def session_factory():
        # async context manager returning the SAME session fixture
        class _CM:
            async def __aenter__(self):
                return session
            async def __aexit__(self, exc_type, exc, tb):
                return False
        return _CM()

    worker = IndexingWorkerService(
        WorkerDeps(
            extractor=PyPDFTextExtractor(),
            chunker=SimpleCharChunker(max_chars=1200, overlap=150),
            embedder_factory=DummyEmbedderFactory(),  # must not be used in extract-only stage
            session_factory=session_factory,
            uow_factory=uow_factory,
            file_storage=file_storage
        )
    )
    # Act: run — you currently comment out the rest and print first 10 lines after extract
    async with session_factory() as session:
        uow = uow_factory(session)
        async with uow:
            _,_,_,storage_path=await worker.load_index_metadata(uow=uow,index_id=index_id)
            text=await worker.extract_text(storage_path=storage_path)
    assert text != ''


async def test_worker_chunks_returns_same_len(session,uow,pdf_bytes, monkeypatch, capsys, tmp_path: Path):
    # Optional: if anything constructs OpenAI factory elsewhere, avoid missing key issues
    if not getattr(settings, "OPENAI_API_KEY", None):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")

    # Build UoW bound to the test session (savepoint-based fixture)

    # 1) Create a real PDF + store it using FilesystemFileStorage (real disk write)
    owner_id = uuid4()


    file_storage = FilesystemFileStorage(base_dir=tmp_path)
    create_project_uc = CreateProjectUseCase(uow=uow, file_storage=file_storage)

    project_out = await create_project_uc.execute(
        CreateProjectInputDTO(
            owner_id=owner_id,
            name="Indexing Extract Test",
            file_bytes=pdf_bytes,
            filename="sample.pdf",
            content_type="application/pdf",
        )
    )

    # 2) Start indexing (runner is stubbed; we’ll run worker directly)
    embed_cfg = EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=16,
        dimensions=None,
    )

    start_indexing_uc = StartIndexingUseCase(
        uow=uow,
        runner=NoopRunner(),
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    )

    await start_indexing_uc.execute(
        StartIndexingInputDTO(
            owner_id=project_out.owner_id,
            project_id=project_out.id,
            document_id=project_out.primary_document.id,
        )
    )

    # Don’t assume DTO shape for index id — fetch via repo using your idempotency signature rule
    async with uow:
        idx = await uow.index_repo.get_latest_active_by_project_and_signature(
            project_id=project_out.id,
            embed_signature=embed_cfg.signature(),
        )
        assert idx is not None
        index_id = idx.id

    def uow_factory(_session):
        # ignore session; return our in-memory uow
        return SqlAlchemyUnitOfWork(_session)
    # simpler: inline async context manager factory
    def session_factory():
        # async context manager returning the SAME session fixture
        class _CM:
            async def __aenter__(self):
                return session
            async def __aexit__(self, exc_type, exc, tb):
                return False
        return _CM()

    worker = IndexingWorkerService(
        WorkerDeps(
            extractor=PyPDFTextExtractor(),
            chunker=SimpleCharChunker(max_chars=1200, overlap=150),
            embedder_factory=DummyEmbedderFactory(),  # must not be used in extract-only stage
            session_factory=session_factory,
            uow_factory=uow_factory,
            file_storage=file_storage
        )
    )

    # Act: run — you currently comment out the rest and print first 10 lines after extract
    async with session_factory() as session:
        uow = uow_factory(session)
        async with uow:
            _,_,_,storage_path=await worker.load_index_metadata(uow=uow,index_id=index_id)
            text=await worker.extract_text(storage_path=storage_path)

    created_chunks = await worker.create_and_store_chunks(index_id=index_id,text=text)
    assert created_chunks != []

    async with session_factory() as session:
        uow = uow_factory(session)
        async with uow:
            retrieved_chunks = await uow.chunk_repo.list_chunks_for_index(index_id=index_id)

    assert len(retrieved_chunks) == len(created_chunks)


async def test_worker_embeds_returns_same_len(session,uow,pdf_bytes, monkeypatch, capsys, tmp_path: Path):
    # Optional: if anything constructs OpenAI factory elsewhere, avoid missing key issues
    if not getattr(settings, "OPENAI_API_KEY", None):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")

    # Build UoW bound to the test session (savepoint-based fixture)

    # 1) Create a real PDF + store it using FilesystemFileStorage (real disk write)
    owner_id = uuid4()


    file_storage = FilesystemFileStorage(base_dir=tmp_path)
    create_project_uc = CreateProjectUseCase(uow=uow, file_storage=file_storage)

    project_out = await create_project_uc.execute(
        CreateProjectInputDTO(
            owner_id=owner_id,
            name="Indexing Extract Test",
            file_bytes=pdf_bytes,
            filename="sample.pdf",
            content_type="application/pdf",
        )
    )

    # 2) Start indexing (runner is stubbed; we’ll run worker directly)
    embed_cfg = EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=16,
        dimensions=1536,
    )

    start_indexing_uc = StartIndexingUseCase(
        uow=uow,
        runner=NoopRunner(),
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    )

    await start_indexing_uc.execute(
        StartIndexingInputDTO(
            owner_id=project_out.owner_id,
            project_id=project_out.id,
            document_id=project_out.primary_document.id,
        )
    )

    # Don’t assume DTO shape for index id — fetch via repo using your idempotency signature rule
    async with uow:
        idx = await uow.index_repo.get_latest_active_by_project_and_signature(
            project_id=project_out.id,
            embed_signature=embed_cfg.signature(),
        )
        assert idx is not None
        index_id = idx.id

    def uow_factory(_session):
        # ignore session; return our in-memory uow
        return SqlAlchemyUnitOfWork(_session)
    # simpler: inline async context manager factory
    def session_factory():
        # async context manager returning the SAME session fixture
        class _CM:
            async def __aenter__(self):
                return session
            async def __aexit__(self, exc_type, exc, tb):
                return False
        return _CM()

    worker = IndexingWorkerService(
        WorkerDeps(
            extractor=PyPDFTextExtractor(),
            chunker=SimpleCharChunker(max_chars=1200, overlap=150),
            embedder_factory=OpenAIEmbedderFactory(api_key=settings.OPENAI_API_KEY),  # must not be used in extract-only stage
            session_factory=session_factory,
            uow_factory=uow_factory,
            file_storage=file_storage
        )
    )

    # Act: run — you currently comment out the rest and print first 10 lines after extract
    async with session_factory() as session:
        uow = uow_factory(session)
        async with uow:
            _,_,_,storage_path=await worker.load_index_metadata(uow=uow,index_id=index_id)
            text=await worker.extract_text(storage_path=storage_path)

    created_chunks = await worker.create_and_store_chunks(index_id=index_id,text=text)
    assert created_chunks != []

    embeds = await worker.embed_chunks(index_id=index_id, chunks=created_chunks,embed_cfg=embed_cfg)
    assert len(embeds) == len(created_chunks)
    assert embeds[0].dim == embed_cfg.dimensions


async def test_worker_store_embeds_persists_and_marks_ready(
    session, uow, pdf_bytes, monkeypatch, tmp_path: Path
):
    # Avoid any accidental OpenAI factory creation elsewhere
    if not getattr(settings, "OPENAI_API_KEY", None):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")

    # 1) Create project + document (writes PDF to tmp_path via real storage)
    owner_id = uuid4()
    file_storage = FilesystemFileStorage(base_dir=tmp_path)
    create_project_uc = CreateProjectUseCase(uow=uow, file_storage=file_storage)

    project_out = await create_project_uc.execute(
        CreateProjectInputDTO(
            owner_id=owner_id,
            name="Indexing Store Embeds Test",
            file_bytes=pdf_bytes,
            filename="sample.pdf",
            content_type="application/pdf",
        )
    )

    # 2) Start indexing (creates DocumentIndex row)
    embed_cfg = EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=16,
        dimensions=8,  # keep small & deterministic for tests
    )

    start_indexing_uc = StartIndexingUseCase(
        uow=uow,
        runner=NoopRunner(),
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    )
    await start_indexing_uc.execute(
        StartIndexingInputDTO(
            owner_id=project_out.owner_id,
            project_id=project_out.id,
            document_id=project_out.primary_document.id,
        )
    )

    # Fetch index_id via your repo rule
    async with uow:
        idx = await uow.index_repo.get_latest_active_by_project_and_signature(
            project_id=project_out.id,
            embed_signature=embed_cfg.signature(),
        )
        assert idx is not None
        index_id = idx.id

    # Session/UoW factories matching your other tests
    def uow_factory(_session):
        return SqlAlchemyUnitOfWork(_session)

    def session_factory():
        class _CM:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return _CM()

    worker = IndexingWorkerService(
        WorkerDeps(
            extractor=PyPDFTextExtractor(),
            chunker=SimpleCharChunker(max_chars=1200, overlap=150),
            embedder_factory=DummyEmbedderFactory(),  # not used
            session_factory=session_factory,
            uow_factory=uow_factory,
            file_storage=file_storage,
        )
    )

    # 3) Extract + chunk + persist chunks
    async with session_factory() as sess:
        uow2 = uow_factory(sess)
        async with uow2:
            _, _, _, storage_path = await worker.load_index_metadata(
                uow=uow2, index_id=index_id
            )
            text = await worker.extract_text(storage_path=storage_path)

    chunks = await worker.create_and_store_chunks(index_id=index_id, text=text)
    assert chunks is not None and len(chunks) > 0

    # 4) Create deterministic fake embeddings aligned with chunks order
    # (Vector.from_list should set dim correctly)
    def make_vec(i: int) -> Vector:
        # Slightly different vector per chunk to ensure mapping is stable
        base = [0.0] * embed_cfg.dimensions
        base[i % embed_cfg.dimensions] = 1.0
        return Vector.from_list(base)

    embeds = [make_vec(i) for i in range(len(chunks))]
    assert len(embeds) == len(chunks)
    assert embeds[0].dim == embed_cfg.dimensions

    # 5) Store embeddings + mark READY
    await worker.store_embeds(
        index_id=index_id,
        chunks=chunks,
        embeds=embeds,
        embed_cfg=embed_cfg,
    )

    # 6) Assert embeddings persisted + index marked READY
    # Count rows
    q_count = select(func.count()).select_from(ChunkEmbeddingModel).where(
        ChunkEmbeddingModel.index_id == index_id
    )
    count1 = await session.scalar(q_count)
    assert count1 == len(chunks)

    # Check embed_signature stored matches
    q_sig = select(ChunkEmbeddingModel.embed_signature).where(
        ChunkEmbeddingModel.index_id == index_id
    )
    sigs = (await session.execute(q_sig)).scalars().all()
    assert sigs and all(s == embed_cfg.signature() for s in sigs)

    # Check index status/progress (adjust field names if different in your model)
    q_idx = select(DocumentIndexModel).where(DocumentIndexModel.id == index_id)
    idx_row = (await session.execute(q_idx)).scalar_one()
    assert idx_row.status.name == "READY" or str(idx_row.status) == "IndexStatus.READY"
    assert idx_row.progress == 100

    # 7) Idempotency: calling store_embeds again should not create duplicates (upsert)
    await worker.store_embeds(
        index_id=index_id,
        chunks=chunks,
        embeds=embeds,
        embed_cfg=embed_cfg,
    )
    count2 = await session.scalar(q_count)
    assert count2 == len(chunks)
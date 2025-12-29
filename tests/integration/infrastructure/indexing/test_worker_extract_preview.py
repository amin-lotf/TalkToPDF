from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest

from talk_to_pdf.backend.app.core import settings
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig
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



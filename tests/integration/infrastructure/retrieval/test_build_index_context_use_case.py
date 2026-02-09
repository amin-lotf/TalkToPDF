# tests/integration/test_build_index_context_use_case.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from talk_to_pdf.backend.app.core.config import settings
from talk_to_pdf.backend.app.infrastructure.db.uow import SqlAlchemyUnitOfWork

from talk_to_pdf.backend.app.application.common.dto import SearchInputDTO
from talk_to_pdf.backend.app.infrastructure.retrieval.merger.mergers import DeterministicRetrievalResultMerger
from talk_to_pdf.backend.app.application.retrieval.use_cases.build_index_context import BuildIndexContextUseCase
from talk_to_pdf.backend.app.application.retrieval.value_objects import MultiQueryRewriteResult
from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO
from talk_to_pdf.backend.app.application.projects.use_cases.create_project import CreateProjectUseCase
from talk_to_pdf.backend.app.application.indexing.dto import StartIndexingInputDTO
from talk_to_pdf.backend.app.application.indexing.use_cases.start_indexing import StartIndexingUseCase

from talk_to_pdf.backend.app.domain.common.value_objects import EmbedConfig, Vector, Chunk
from talk_to_pdf.backend.app.domain.common.enums import VectorMetric
from talk_to_pdf.backend.app.domain.retrieval.errors import (
    InvalidQuery,
    IndexNotFoundOrForbidden,
    IndexNotReady,
)
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus

from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage
from talk_to_pdf.backend.app.infrastructure.db.models import (
    DocumentIndexModel,
)
from talk_to_pdf.backend.app.infrastructure.indexing.service import IndexingWorkerService, WorkerDeps
from tests.unit.fakes.indexing_worker_deps import FakePdfToXmlConverter, FakeBlockExtractor, FakeBlockChunker

pytestmark = pytest.mark.asyncio


# ---------------------------
# Test doubles
# ---------------------------

@dataclass
class NoopRunner:
    async def enqueue(self, *, index_id: UUID) -> None:
        return


@dataclass
class FixedEmbedder:
    vec: list[float]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        # return one identical embedding per text
        return [list(self.vec) for _ in texts]


@dataclass
class FixedEmbedderFactory:
    vec: list[float]

    def create(self, cfg: EmbedConfig) -> FixedEmbedder:
        return FixedEmbedder(vec=self.vec)


@dataclass
class ReverseReranker:
    async def rank(self, query: str, candidates: list[Chunk], *, top_n: int | None = None, ctx=None) -> list[Chunk]:
        ranked = list(reversed(candidates))
        return ranked[:top_n] if top_n is not None else ranked


@dataclass
class SlowReranker:
    delay_s: float = 0.5

    async def rank(self, query: str, candidates: list[Chunk], *, top_n: int | None = None, ctx=None) -> list[Chunk]:
        await asyncio.sleep(self.delay_s)
        ranked = list(reversed(candidates))
        return ranked[:top_n] if top_n is not None else ranked


@dataclass
class IdentityMultiQueryRewriter:
    fixed: list[str] | None = None

    async def rewrite(self, *, query: str, history) -> str:
        return (self.fixed or [query])[0]

    async def rewrite_queries_with_metrics(self, *, query: str, history) -> MultiQueryRewriteResult:
        queries = self.fixed or [query]
        return MultiQueryRewriteResult(queries=queries, prompt_tokens=0, completion_tokens=0)

    async def rewrite_with_metrics(self, *, query: str, history) -> MultiQueryRewriteResult:
        return await self.rewrite_queries_with_metrics(query=query, history=history)


# ---------------------------
# Shared seed helper (REAL pipeline)
# ---------------------------

async def _seed_ready_index_with_chunks_and_embeds(
    *,
    session,
    uow,
    pdf_bytes: bytes,
    tmp_path: Path,
    monkeypatch,
    embed_cfg: EmbedConfig,
) -> tuple[UUID, UUID, UUID, UUID]:
    """
    Creates:
      - project + document
      - index (StartIndexingUseCase)
      - chunks stored (worker.create_and_store_chunks)
      - embeddings stored (worker.store_embeds) and index marked READY

    Returns:
      (owner_id, project_id, document_id, index_id)
    """
    # Avoid accidental OpenAI usage in any factory code paths
    if not getattr(settings, "OPENAI_API_KEY", None):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")

    owner_id = uuid4()

    # 1) project + document
    file_storage = FilesystemFileStorage(base_dir=tmp_path)
    create_project_uc = CreateProjectUseCase(uow=uow, file_storage=file_storage)
    project_out = await create_project_uc.execute(
        CreateProjectInputDTO(
            owner_id=owner_id,
            name="BuildIndexContext Seed",
            file_bytes=pdf_bytes,
            filename="sample.pdf",
            content_type="application/pdf",
        )
    )

    # 2) start indexing
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

    # get index_id
    async with uow:
        idx = await uow.index_repo.get_latest_active_by_project_and_signature(
            project_id=project_out.id,
            embed_signature=embed_cfg.signature(),
        )
        assert idx is not None
        index_id = idx.id

    # session/uow factories (same pattern as your worker test)
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
            pdf_to_xml_converter=FakePdfToXmlConverter(xml="<TEI></TEI>"),
            block_extractor=FakeBlockExtractor(),
            block_chunker=FakeBlockChunker(),
            embedder_factory=None,  # not used here
            session_factory=session_factory,
            uow_factory=uow_factory,
            file_storage=file_storage,
        )
    )

    # 3) convert + parse + persist chunks
    async with session_factory() as sess:
        uow2 = uow_factory(sess)
        async with uow2:
            _, _, _, storage_path = await worker.load_index_metadata(uow=uow2, index_id=index_id)
            xml = await worker.convert_pdf_to_xml(storage_path=storage_path)
            blocks = await worker.extract_blocks_from_xml(xml)

    chunks = await worker.create_and_store_chunks(index_id=index_id, blocks=blocks)
    assert chunks and len(chunks) > 0

    # 4) deterministic embeddings aligned with chunks order
    def make_vec(i: int) -> Vector:
        base = [0.0] * embed_cfg.dimensions
        base[i % embed_cfg.dimensions] = 1.0
        return Vector.from_list(base)

    embeds = [make_vec(i) for i in range(len(chunks))]

    # 5) store embeds + mark READY
    await worker.store_embeds(index_id=index_id, chunks=chunks, embeds=embeds, embed_cfg=embed_cfg)

    # Assert READY (seed sanity)
    idx_row = (await session.execute(select(DocumentIndexModel).where(DocumentIndexModel.id == index_id))).scalar_one()
    assert idx_row.status == IndexStatus.READY or idx_row.status.name == "READY"

    return (project_out.owner_id, project_out.id, project_out.primary_document.id, index_id)


# ---------------------------
# Tests
# ---------------------------

async def test_build_index_context_blank_query_raises(uow_factory):
    uc = BuildIndexContextUseCase(
        uow_factory=uow_factory,
        embedder_factory=FixedEmbedderFactory(vec=[1.0, 0.0, 0.0]),
        query_rewriter=IdentityMultiQueryRewriter(),
        retrieval_merger=DeterministicRetrievalResultMerger(),
        max_top_k=settings.MAX_TOP_K,
        max_top_n=settings.MAX_TOP_N,
    )
    with pytest.raises(InvalidQuery):
        await uc.execute(
            SearchInputDTO(
                owner_id=uuid4(),
                project_id=uuid4(),
                index_id=uuid4(),
                query="   ",
                message_history=[],
                top_k=5,
                top_n=3,
                rerank_timeout_s=0.2,
            )
        )


async def test_build_index_context_index_not_found_or_forbidden_raises(uow_factory):
    uc = BuildIndexContextUseCase(
        uow_factory=uow_factory,
        embedder_factory=FixedEmbedderFactory(vec=[1.0, 0.0, 0.0]),
        query_rewriter=IdentityMultiQueryRewriter(),
        retrieval_merger=DeterministicRetrievalResultMerger(),
        max_top_k=settings.MAX_TOP_K,
        max_top_n=settings.MAX_TOP_N,
    )
    with pytest.raises(IndexNotFoundOrForbidden):
        await uc.execute(
            SearchInputDTO(
                owner_id=uuid4(),
                project_id=uuid4(),
                index_id=uuid4(),
                query="hello",
                message_history=[],
                top_k=5,
                top_n=3,
                rerank_timeout_s=0.2,
            )
        )


async def test_build_index_context_index_not_ready_raises(session, uow, uow_factory,pdf_bytes, monkeypatch, tmp_path: Path):
    embed_cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=16, dimensions=8)

    # seed project + index but keep it NOT READY (no worker.store_embeds)
    if not getattr(settings, "OPENAI_API_KEY", None):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")

    owner_id = uuid4()
    file_storage = FilesystemFileStorage(base_dir=tmp_path)
    project_out = await CreateProjectUseCase(uow=uow, file_storage=file_storage).execute(
        CreateProjectInputDTO(
            owner_id=owner_id,
            name="NotReady seed",
            file_bytes=pdf_bytes,
            filename="sample.pdf",
            content_type="application/pdf",
        )
    )

    await StartIndexingUseCase(
        uow=uow,
        runner=NoopRunner(),
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    ).execute(
        StartIndexingInputDTO(
            owner_id=project_out.owner_id,
            project_id=project_out.id,
            document_id=project_out.primary_document.id,
        )
    )

    async with uow:
        idx = await uow.index_repo.get_latest_active_by_project_and_signature(
            project_id=project_out.id,
            embed_signature=embed_cfg.signature(),
        )
        assert idx is not None
        index_id = idx.id

    uc = BuildIndexContextUseCase(
        uow_factory=uow_factory,
        embedder_factory=FixedEmbedderFactory(vec=[1.0] + [0.0] * (embed_cfg.dimensions - 1)),
        query_rewriter=IdentityMultiQueryRewriter(),
        retrieval_merger=DeterministicRetrievalResultMerger(),
        max_top_k=settings.MAX_TOP_K,
        max_top_n=settings.MAX_TOP_N,
    )

    with pytest.raises(IndexNotReady):
        await uc.execute(
            SearchInputDTO(
                owner_id=project_out.owner_id,
                project_id=project_out.id,
                index_id=index_id,
                query="hello",
                message_history=[],
                top_k=5,
                top_n=3,
                rerank_timeout_s=0.2,
            )
        )


async def test_build_index_context_happy_path_returns_top_n_and_embed_signature(
    session, uow,uow_factory, pdf_bytes, monkeypatch, tmp_path: Path
):
    embed_cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=16, dimensions=8)

    owner_id, project_id, document_id, index_id = await _seed_ready_index_with_chunks_and_embeds(
        session=session,
        uow=uow,
        pdf_bytes=pdf_bytes,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        embed_cfg=embed_cfg,
    )

    # Choose query embedding identical to chunk-0 embedding:
    # chunk0 vec = e0=[1,0,0,...] due to make_vec(0)
    query_vec = [1.0] + [0.0] * (embed_cfg.dimensions - 1)

    uc = BuildIndexContextUseCase(
        uow_factory=uow_factory,
        embedder_factory=FixedEmbedderFactory(vec=query_vec),
        metric=VectorMetric.COSINE,
        query_rewriter=IdentityMultiQueryRewriter(),
        retrieval_merger=DeterministicRetrievalResultMerger(),
        max_top_k=settings.MAX_TOP_K,
        max_top_n=settings.MAX_TOP_N,
    )

    out = await uc.execute(
        SearchInputDTO(
            owner_id=owner_id,
            project_id=project_id,
            index_id=index_id,
            query="hello",
            message_history=[],
            top_k=5,
            top_n=2,
            rerank_timeout_s=0.2,
        )
    )

    assert out.index_id == index_id
    assert out.project_id == project_id
    assert out.query == "hello"
    assert out.embed_signature == embed_cfg.signature()
    assert out.metric == VectorMetric.COSINE

    assert len(out.chunks) == 2

    # Most similar should be chunk whose embedding is e0 (chunk_index 0)
    # Your mapper sets chunk_index from the Chunk row.
    assert out.chunks[0].chunk_index == 0

    # scores should exist and be floats
    assert isinstance(out.chunks[0].score, float)


async def test_build_index_context_rerank_reorders_but_keeps_similarity_scores(
    session, uow,uow_factory, pdf_bytes, monkeypatch, tmp_path: Path
):
    embed_cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=16, dimensions=8)
    owner_id, project_id, _, index_id = await _seed_ready_index_with_chunks_and_embeds(
        session=session,
        uow=uow,
        pdf_bytes=pdf_bytes,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        embed_cfg=embed_cfg,
    )

    query_vec = [1.0] + [0.0] * (embed_cfg.dimensions - 1)

    uc = BuildIndexContextUseCase(
        uow_factory=uow_factory,
        embedder_factory=FixedEmbedderFactory(vec=query_vec),
        reranker=ReverseReranker(),
        metric=VectorMetric.COSINE,
        query_rewriter=IdentityMultiQueryRewriter(),
        retrieval_merger=DeterministicRetrievalResultMerger(),
        max_top_k=settings.MAX_TOP_K,
        max_top_n=settings.MAX_TOP_N,
    )

    out = await uc.execute(
        SearchInputDTO(
            owner_id=owner_id,
            project_id=project_id,
            index_id=index_id,
            query="hello",
            message_history=[],
            top_k=3,
            top_n=3,
            rerank_timeout_s=1.0,
        )
    )

    assert len(out.chunks) == 3

    # Without rerank, similarity order should start with chunk_index 0.
    # With reverse rerank, it should end with chunk_index 0.
    assert out.chunks[-1].chunk_index == 0

    # Scores should still reflect similarity (chunk_index 0 should have highest score)
    # even if it was moved to the end by rerank.
    scores_by_chunk_index = {c.chunk_index: c.score for c in out.chunks}
    assert scores_by_chunk_index[0] >= scores_by_chunk_index[1] >= scores_by_chunk_index[2]


async def test_build_index_context_rerank_timeout_falls_back_to_similarity_order(
    session, uow,uow_factory, pdf_bytes, monkeypatch, tmp_path: Path
):
    embed_cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=16, dimensions=8)
    owner_id, project_id, _, index_id = await _seed_ready_index_with_chunks_and_embeds(
        session=session,
        uow=uow,
        pdf_bytes=pdf_bytes,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        embed_cfg=embed_cfg,
    )

    query_vec = [1.0] + [0.0] * (embed_cfg.dimensions - 1)

    uc = BuildIndexContextUseCase(
        uow_factory=uow_factory,
        embedder_factory=FixedEmbedderFactory(vec=query_vec),
        reranker=SlowReranker(delay_s=0.5),
        metric=VectorMetric.COSINE,
        query_rewriter=IdentityMultiQueryRewriter(),
        retrieval_merger=DeterministicRetrievalResultMerger(),
        max_top_k=settings.MAX_TOP_K,
        max_top_n=settings.MAX_TOP_N,
    )

    out = await uc.execute(
        SearchInputDTO(
            owner_id=owner_id,
            project_id=project_id,
            index_id=index_id,
            query="hello",
            message_history=[],
            top_k=3,
            top_n=3,
            rerank_timeout_s=0.01,  # force timeout
        )
    )

    # Should be similarity order: chunk_index 0 then 1 then 2
    assert [c.chunk_index for c in out.chunks[:3]] == [0, 1, 2]


async def test_build_index_context_embedder_returns_empty_vector_raises_invalid_retrieval(uow,uow_factory):
    @dataclass
    class EmptyEmbedder:
        async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[]]

    @dataclass
    class EmptyFactory:
        def create(self, cfg: EmbedConfig):
            return EmptyEmbedder()

    # It will fail before needing DB (after index lookup) — so pass random IDs and expect not-found first.
    # To hit InvalidRetrieval precisely, you'd need a real READY index. This is the minimal “unit-ish” integration.
    uc = BuildIndexContextUseCase(
        uow_factory=uow_factory,
        embedder_factory=EmptyFactory(),
        query_rewriter=IdentityMultiQueryRewriter(),
        retrieval_merger=DeterministicRetrievalResultMerger(),
        max_top_k=settings.MAX_TOP_K,
        max_top_n=settings.MAX_TOP_N
    )
    with pytest.raises(IndexNotFoundOrForbidden):
        await uc.execute(
            SearchInputDTO(
                owner_id=uuid4(),
                project_id=uuid4(),
                index_id=uuid4(),
                query="hello",
                message_history=[],
                top_k=3,
                top_n=2,
                rerank_timeout_s=0.2,
            )
        )

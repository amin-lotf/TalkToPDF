from __future__ import annotations

from uuid import uuid4

import pytest

from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig
from talk_to_pdf.backend.app.domain.projects import Project, ProjectName
from talk_to_pdf.backend.app.domain.projects.entities import ProjectDocument
from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.simple_char_chunker import SimpleCharChunker
from talk_to_pdf.backend.app.infrastructure.indexing.service import IndexingWorkerService, WorkerDeps

from tests.unit.fakes.indexing_worker_deps import (
    FakeEmbedder,
    FakeEmbedderFactory,
    FakeSession,
    FakeSessionContext,
    FakeTextExtractor,
)


@pytest.mark.asyncio
async def test_worker_happy_path_marks_ready_and_creates_chunks(uow,tmp_path):
    # Arrange: create a real path (worker resolves it from Project.primary_document.storage_path)
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("not-a-real-pdf")  # extractor is faked; file just needs to exist as a path

    session = FakeSession()

    # Create real Project + ProjectDocument and store via fake repo
    owner_id = uuid4()
    project = Project(name=ProjectName("Test"), owner_id=owner_id)
    document_id = uuid4()
    project_doc = ProjectDocument(
        project_id=project.id,
        original_filename="doc.pdf",
        storage_path=str(pdf_path),
        content_type="application/pdf",
        size_bytes=pdf_path.stat().st_size,
    )
    project = project.attach_main_document(project_doc)
    await uow.project_repo.add(project)

    # Create a real DocumentIndex via repo (so fields match your mapper expectations)
    cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=2, dimensions=3)
    created_index = await uow.index_repo.create_pending(
        project_id=project.id,
        document_id=document_id,
        chunker_version="v1",
        embed_config=cfg,
    )
    index_id = created_index.id

    extractor = FakeTextExtractor(text="A" * 2600)  # should produce multiple chunks
    chunker = SimpleCharChunker(max_chars=1200, overlap=150)
    embedder = FakeEmbedder(dims=3)
    embedder_factory = FakeEmbedderFactory(embedder)

    def session_factory():
        return FakeSessionContext(session)

    def uow_factory(_session):
        # ignore session; return our in-memory uow
        return uow

    worker = IndexingWorkerService(
        WorkerDeps(
            extractor=extractor,
            chunker=chunker,
            embedder_factory=embedder_factory,
            session_factory=session_factory,
            uow_factory=uow_factory,  # type: ignore[arg-type]
        )
    )

    # Act
    await worker.run(index_id=index_id)

    # Assert: chunks were created for this index
    assert index_id in uow.chunk_repo._by_index  # fake repo internal storage
    assert len(uow.chunk_repo._by_index[index_id]) >= 2

    # Assert: index ends READY at 100
    final = await uow.index_repo.get_by_id(index_id=index_id)
    assert final is not None
    assert final.status == IndexStatus.READY
    assert final.progress == 100

    # Assert: embedder actually called
    assert embedder.calls, "Expected embedder to be invoked"

    # Assert: at least one mid-job commit happened for progress visibility
    assert session.commits >= 1


# @pytest.mark.asyncio
# async def test_worker_extractor_failure_marks_failed(uow):
#     session = FakeSession()
#
#     index_id = uuid4()
#     cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=2, dimensions=3)
#     uow.index_repo.by_id[index_id] = DocumentIndex(
#         id=index_id,
#         project_id=project_id,
#         document_id=document_id,
#         embed_config=cfg,
#         cancel_requested=False,
#         status=IndexStatus.PENDING,
#         progress=0,
#         message="Queued",
#         error=None,
#         chunker_version="v1",
#     )
#
#     extractor = FakeTextExtractor(raise_exc=RuntimeError("boom"))
#     chunker = SimpleCharChunker()
#     embedder_factory = FakeEmbedderFactory(FakeEmbedder())
#
#     worker = IndexingWorkerService(
#         WorkerDeps(
#             extractor=extractor,
#             chunker=chunker,
#             embedder_factory=embedder_factory,
#             session_factory=lambda: FakeSessionContext(session),
#             uow_factory=lambda _s: uow,  # type: ignore[arg-type]
#         )
#     )
#
#     await worker.run(index_id=index_id)
#
#     assert uow.index_repo.progress_updates, "Expected progress updates"
#     last = uow.index_repo.progress_updates[-1]
#     assert last["status"] == IndexStatus.FAILED
#     assert last["message"] == "Failed to extract text"
#     assert "boom" in (last["error"] or "")
#
#
# @pytest.mark.asyncio
# async def test_worker_cancel_before_start_marks_cancelled_and_deletes_artifacts(uow):
#     session = FakeSession()
#
#     index_id = uuid4()
#     cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=2, dimensions=3)
#     uow.index_repo.by_id[index_id] = FakeDocumentIndex(
#         id=index_id,
#         project_id=uuid4(),
#         document_id=uuid4(),
#         embed_config=cfg.to_dict(),
#         cancel_requested=True,  # cancelled immediately
#     )
#
#     worker = IndexingWorkerService(
#         WorkerDeps(
#             extractor=FakeTextExtractor(text="should not be used"),
#             chunker=SimpleCharChunker(),
#             embedder_factory=FakeEmbedderFactory(FakeEmbedder()),
#             session_factory=lambda: FakeSessionContext(session),
#             uow_factory=lambda _s: uow,  # type: ignore[arg-type]
#         )
#     )
#
#     await worker.run(index_id=index_id)
#
#     # ensured delete artifacts called
#     assert index_id in uow.index_repo.deleted_artifacts
#
#     # should set CANCELLED status at some point
#     statuses = [u["status"] for u in uow.index_repo.progress_updates]
#     assert IndexStatus.CANCELLED in statuses

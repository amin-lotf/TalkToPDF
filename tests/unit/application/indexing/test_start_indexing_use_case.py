from __future__ import annotations
from datetime import timedelta
from talk_to_pdf.backend.app.domain.common import utcnow
from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex

from uuid import uuid4, UUID

import pytest

from talk_to_pdf.backend.app.application.indexing.dto import StartIndexingInputDTO
from talk_to_pdf.backend.app.application.indexing.use_cases.start_indexing import StartIndexingUseCase
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.errors import FailedToStartIndexing
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig
from tests.unit.fakes.indexing_runner import FakeIndexingRunner

class RecordingFailRunner:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.enqueued: list[UUID] = []

    async def enqueue(self, *, index_id: UUID) -> None:
        self.enqueued.append(index_id)
        raise self.exc

    async def stop(self, *, index_id: UUID) -> None:
        return None

@pytest.mark.asyncio
async def test_start_indexing_idempotent_returns_latest_active(uow):
    # Arrange
    runner = FakeIndexingRunner()

    cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=2, dimensions=3)

    project_id = uuid4()
    existing = DocumentIndex(
        project_id=project_id,
        document_id=uuid4(),
        chunker_version="v1",
        embed_config=cfg,
        status=IndexStatus.RUNNING,   # ACTIVE -> should trigger idempotency hit
        progress=10,
        updated_at=utcnow() + timedelta(seconds=1),
    )

    # store existing index in fake repo
    # NOTE: if your fake repo uses a different internal dict name, adjust here.
    uow.index_repo._by_id[existing.id] = existing

    uc = StartIndexingUseCase(
        uow=uow,
        runner=runner,
        chunker_version="v1",
        embed_config=cfg,
    )

    dto = StartIndexingInputDTO(project_id=project_id, document_id=uuid4())

    # Act
    out = await uc.execute(dto)

    # Assert
    assert out.index_id == existing.id
    assert out.project_id == existing.project_id
    assert out.status == existing.status
    assert runner.enqueued == []  # idempotency hit => don't enqueue





@pytest.mark.asyncio
async def test_start_indexing_enqueue_failure_marks_failed_and_raises(uow):
    # Arrange
    runner = RecordingFailRunner(RuntimeError("queue down"))

    cfg = EmbedConfig(provider="openai", model="text-embedding-3-small", batch_size=2, dimensions=3)

    uc = StartIndexingUseCase(
        uow=uow,
        runner=runner,
        chunker_version="v1",
        embed_config=cfg,
    )

    dto = StartIndexingInputDTO(project_id=uuid4(), document_id=uuid4())

    # Act + Assert (use case raises clean domain error)
    with pytest.raises(FailedToStartIndexing):
        await uc.execute(dto)

    # The runner should have been called once with the created index id
    assert len(runner.enqueued) == 1
    created_id = runner.enqueued[0]

    # The index should be marked FAILED in a follow-up transaction
    idx = await uow.index_repo.get_by_id(index_id=created_id)
    assert idx is not None
    assert idx.status == IndexStatus.FAILED
    assert idx.progress == 0
    assert idx.message == "Failed to enqueue indexing job"
    assert "queue down" in (idx.error or "")
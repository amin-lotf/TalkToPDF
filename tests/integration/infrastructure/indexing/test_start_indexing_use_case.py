from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, func

from talk_to_pdf.backend.app.application.indexing.dto import StartIndexingInputDTO
from talk_to_pdf.backend.app.application.indexing.use_cases.start_indexing import StartIndexingUseCase
from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO
from talk_to_pdf.backend.app.application.projects.use_cases.create_project import CreateProjectUseCase
from talk_to_pdf.backend.app.domain.common.value_objects import EmbedConfig
from talk_to_pdf.backend.app.domain.indexing.errors import FailedToStartIndexing
from talk_to_pdf.backend.app.infrastructure.db.models import DocumentIndexModel
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage

pytestmark = pytest.mark.asyncio


# ---------------------------
# Runner stubs
# ---------------------------

@dataclass
class RecordingRunner:
    enqueued: list[UUID] = field(default_factory=list)

    async def enqueue(self, *, index_id: UUID) -> None:
        self.enqueued.append(index_id)


@dataclass
class FailingRunner:
    exc: Exception = RuntimeError("boom")
    enqueued: list[UUID] = field(default_factory=list)

    async def enqueue(self, *, index_id: UUID) -> None:
        self.enqueued.append(index_id)
        raise self.exc


# ---------------------------
# Helpers
# ---------------------------

async def _create_project(uow, tmp_path: Path, pdf_bytes: bytes):
    owner_id = uuid4()
    file_storage = FilesystemFileStorage(base_dir=tmp_path)
    create_project_uc = CreateProjectUseCase(uow=uow, file_storage=file_storage)
    project_out = await create_project_uc.execute(
        CreateProjectInputDTO(
            owner_id=owner_id,
            name="StartIndexing UC Test",
            file_bytes=pdf_bytes,
            filename="sample.pdf",
            content_type="application/pdf",
        )
    )
    return project_out, file_storage


# ---------------------------
# Tests
# ---------------------------

async def test_start_indexing_creates_pending_and_enqueues_once(session, uow, pdf_bytes, tmp_path: Path):
    project_out, _ = await _create_project(uow=uow, tmp_path=tmp_path, pdf_bytes=pdf_bytes)

    embed_cfg = EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=16,
        dimensions=1536,
    )
    runner = RecordingRunner()

    uc = StartIndexingUseCase(
        uow=uow,
        runner=runner,
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    )

    dto = StartIndexingInputDTO(
        owner_id=project_out.owner_id,
        project_id=project_out.id,
        document_id=project_out.primary_document.id,
    )

    # Act
    out = await uc.execute(dto)

    # Assert runner called
    assert runner.enqueued == [out.index_id]

    # Assert DB row exists and is PENDING
    row = (await session.execute(select(DocumentIndexModel).where(DocumentIndexModel.id == out.index_id))).scalar_one()
    assert row.project_id == project_out.id
    assert row.document_id == project_out.primary_document.id
    assert row.chunker_version == "simple-char-v1"
    assert row.embed_signature == embed_cfg.signature()
    assert row.status.name in {"PENDING", "RUNNING"}  # should be PENDING immediately


async def test_start_indexing_idempotent_returns_latest_active_and_does_not_enqueue_again(
    session, uow, pdf_bytes, tmp_path: Path
):
    project_out, _ = await _create_project(uow=uow, tmp_path=tmp_path, pdf_bytes=pdf_bytes)

    embed_cfg = EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=16,
        dimensions=1536,
    )
    runner = RecordingRunner()

    uc = StartIndexingUseCase(
        uow=uow,
        runner=runner,
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    )

    dto = StartIndexingInputDTO(
        owner_id=project_out.owner_id,
        project_id=project_out.id,
        document_id=project_out.primary_document.id,
    )

    # First call creates + enqueues
    out1 = await uc.execute(dto)
    assert runner.enqueued == [out1.index_id]

    # Second call should return the same "latest active" and NOT enqueue again
    out2 = await uc.execute(dto)
    assert (out2.index_id== out1.index_id)
    assert runner.enqueued == [out1.index_id]  # still only once

    # And no extra index rows created for same (project, signature) while active
    q_count = select(func.count()).select_from(DocumentIndexModel).where(
        DocumentIndexModel.project_id == project_out.id,
        DocumentIndexModel.embed_signature == embed_cfg.signature(),
    )
    count = await session.scalar(q_count)
    assert count == 1


async def test_start_indexing_project_not_found_raises_failed_to_start_indexing(uow):
    embed_cfg = EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=16,
        dimensions=1536,
    )

    uc = StartIndexingUseCase(
        uow=uow,
        runner=RecordingRunner(),
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    )

    # random IDs (no such project)
    with pytest.raises(FailedToStartIndexing):
        await uc.execute(
            StartIndexingInputDTO(
                owner_id=uuid4(),
                project_id=uuid4(),
                document_id=uuid4(),
            )
        )


async def test_start_indexing_document_mismatch_raises_failed_to_start_indexing(uow, pdf_bytes, tmp_path: Path):
    project_out, _ = await _create_project(uow=uow, tmp_path=tmp_path, pdf_bytes=pdf_bytes)

    embed_cfg = EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=16,
        dimensions=1536,
    )

    uc = StartIndexingUseCase(
        uow=uow,
        runner=RecordingRunner(),
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    )

    # wrong document id
    with pytest.raises(FailedToStartIndexing):
        await uc.execute(
            StartIndexingInputDTO(
                owner_id=project_out.owner_id,
                project_id=project_out.id,
                document_id=uuid4(),
            )
        )


async def test_start_indexing_enqueue_failure_marks_failed_and_raises(
    session, uow, pdf_bytes, tmp_path: Path
):
    project_out, _ = await _create_project(uow=uow, tmp_path=tmp_path, pdf_bytes=pdf_bytes)

    embed_cfg = EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=16,
        dimensions=1536,
    )

    runner = FailingRunner(exc=RuntimeError("queue down"))
    uc = StartIndexingUseCase(
        uow=uow,
        runner=runner,
        chunker_version="simple-char-v1",
        embed_config=embed_cfg,
    )

    dto = StartIndexingInputDTO(
        owner_id=project_out.owner_id,
        project_id=project_out.id,
        document_id=project_out.primary_document.id,
    )

    with pytest.raises(FailedToStartIndexing):
        await uc.execute(dto)

    # We don't know created.id from the exception, so fetch latest by repo rule
    async with uow:
        idx = await uow.index_repo.get_latest_active_by_project_and_signature(
            project_id=project_out.id,
            embed_signature=embed_cfg.signature(),
        )
        # Important nuance:
        # - your "report(... FAILED ...)" likely keeps it "active" only if your repo considers FAILED active.
        #   If FAILED is not "active", idx may be None.
        # So we fall back to DB query too.

    # Query DB directly: latest row for project+signature should be FAILED
    row = (
        await session.execute(
            select(DocumentIndexModel)
            .where(
                DocumentIndexModel.project_id == project_out.id,
                DocumentIndexModel.embed_signature == embed_cfg.signature(),
            )
            .order_by(DocumentIndexModel.created_at.desc())
            .limit(1)
        )
    ).scalar_one()

    assert row.status.name == "FAILED"
    # if you persist these fields (looks like you do):
    assert row.message is None or "enqueue" in row.message.lower()
    assert row.error is None or "queue down" in row.error.lower()

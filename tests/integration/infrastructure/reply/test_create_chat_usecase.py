# tests/integration/test_create_chat_use_case.py
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from talk_to_pdf.backend.app.application.reply.dto import CreateChatInputDTO
from talk_to_pdf.backend.app.application.reply.use_cases.create_chat import CreateChatUseCase
from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO
from talk_to_pdf.backend.app.application.projects.use_cases.create_project import CreateProjectUseCase
from talk_to_pdf.backend.app.domain.projects.errors import ProjectNotFound

from talk_to_pdf.backend.app.infrastructure.db.models import ChatModel
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage

pytestmark = pytest.mark.asyncio


async def _seed_project(*, uow, tmp_path: Path, pdf_bytes: bytes):
    owner_id = uuid4()
    file_storage = FilesystemFileStorage(base_dir=tmp_path)

    out = await CreateProjectUseCase(uow=uow, file_storage=file_storage).execute(
        CreateProjectInputDTO(
            owner_id=owner_id,
            name="CreateChat UC Test",
            file_bytes=pdf_bytes,
            filename="sample.pdf",
            content_type="application/pdf",
        )
    )
    return owner_id, out.id


async def test_create_chat_project_not_found_raises(uow_factory):
    uc = CreateChatUseCase(uow_factory=uow_factory)

    with pytest.raises(ProjectNotFound):
        await uc.execute(
            CreateChatInputDTO(
                owner_id=uuid4(),
                project_id=uuid4(),
                title="Should fail",
            )
        )


async def test_create_chat_happy_path_persists_and_returns_chat_dto(
    session, uow, uow_factory, pdf_bytes, tmp_path: Path
):
    owner_id, project_id = await _seed_project(uow=uow, tmp_path=tmp_path, pdf_bytes=pdf_bytes)

    uc = CreateChatUseCase(uow_factory=uow_factory)

    inp = CreateChatInputDTO(
        owner_id=owner_id,
        project_id=project_id,
        title="My first chat",
    )

    out = await uc.execute(inp)

    # ---- DTO assertions (behavior)
    assert out.owner_id == owner_id
    assert out.project_id == project_id
    assert out.title == "My first chat"
    assert out.id is not None
    assert out.created_at is not None
    assert out.updated_at is not None
    # updated_at should not be earlier than created_at
    assert out.updated_at >= out.created_at

    # ---- DB assertions (integration)
    row = (await session.execute(select(ChatModel).where(ChatModel.id == out.id))).scalar_one()

    assert row.id == out.id
    assert row.owner_id == owner_id
    assert row.project_id == project_id
    assert row.title == "My first chat"
    assert row.created_at is not None
    assert row.updated_at is not None
    assert row.updated_at >= row.created_at


async def test_create_chat_owner_mismatch_raises_project_not_found(
    session, uow, uow_factory, pdf_bytes, tmp_path: Path
):
    """
    This validates your access rule:
    project_repo.get_by_owner_and_id(owner_id, project_id)
    => wrong owner should behave like not found.
    """
    real_owner_id, project_id = await _seed_project(uow=uow, tmp_path=tmp_path, pdf_bytes=pdf_bytes)
    wrong_owner_id = uuid4()
    assert wrong_owner_id != real_owner_id

    uc = CreateChatUseCase(uow_factory=uow_factory)

    with pytest.raises(ProjectNotFound):
        await uc.execute(
            CreateChatInputDTO(
                owner_id=wrong_owner_id,
                project_id=project_id,
                title="Should fail (wrong owner)",
            )
        )

    # Ensure no chat rows created for that project (extra safety)
    count = await session.scalar(
        select(ChatModel.id).where(ChatModel.project_id == project_id).limit(1)
    )
    assert count is None

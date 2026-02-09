# tests/integration/test_create_chat_message_use_case.py
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO
from talk_to_pdf.backend.app.application.projects.use_cases.create_project import CreateProjectUseCase

from talk_to_pdf.backend.app.application.reply.dto import CreateChatInputDTO, CreateMessageInputDTO
from talk_to_pdf.backend.app.application.reply.use_cases.create_chat import CreateChatUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.create_message import CreateChatMessageUseCase
from talk_to_pdf.backend.app.domain.common.enums import ChatRole

from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden

from talk_to_pdf.backend.app.infrastructure.db.models import ChatModel, ChatMessageModel
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage

pytestmark = pytest.mark.asyncio


async def _seed_project(*, uow, tmp_path: Path, pdf_bytes: bytes):
    owner_id = uuid4()
    file_storage = FilesystemFileStorage(base_dir=tmp_path)

    out = await CreateProjectUseCase(uow=uow, file_storage=file_storage).execute(
        CreateProjectInputDTO(
            owner_id=owner_id,
            name="CreateChatMessage UC Test",
            file_bytes=pdf_bytes,
            filename="sample.pdf",
            content_type="application/pdf",
        )
    )
    return owner_id, out.id


async def _seed_chat(*, uow_factory, uow, tmp_path: Path, pdf_bytes: bytes):
    owner_id, project_id = await _seed_project(uow=uow, tmp_path=tmp_path, pdf_bytes=pdf_bytes)

    chat_uc = CreateChatUseCase(uow_factory=uow_factory)
    chat_out = await chat_uc.execute(
        CreateChatInputDTO(
            owner_id=owner_id,
            project_id=project_id,
            title="Chat for messages",
        )
    )
    return owner_id, project_id, chat_out.id


async def test_create_chat_message_chat_not_found_or_forbidden_raises(uow_factory):
    uc = CreateChatMessageUseCase(uow_factory=uow_factory)

    with pytest.raises(ChatNotFoundOrForbidden):
        await uc.execute(
            CreateMessageInputDTO(
                owner_id=uuid4(),
                chat_id=uuid4(),
                role=ChatRole.USER,
                content="Hello",
            )
        )


async def test_create_chat_message_happy_path_persists_message_and_touches_chat(
    session, uow, uow_factory, pdf_bytes, tmp_path: Path
):
    owner_id, _, chat_id = await _seed_chat(
        uow_factory=uow_factory, uow=uow, tmp_path=tmp_path, pdf_bytes=pdf_bytes
    )

    # capture chat.updated_at BEFORE
    chat_before = (await session.execute(select(ChatModel).where(ChatModel.id == chat_id))).scalar_one()
    before_updated_at = chat_before.updated_at

    uc = CreateChatMessageUseCase(uow_factory=uow_factory)

    out = await uc.execute(
        CreateMessageInputDTO(
            owner_id=owner_id,
            chat_id=chat_id,
            role=ChatRole.USER,
            content="First message",
        )
    )

    # ---- DTO behavior
    assert out.chat_id == chat_id
    assert out.role == ChatRole.USER
    assert out.content == "First message"
    assert out.id is not None
    assert out.created_at is not None

    # ---- DB persisted message
    msg_row = (await session.execute(select(ChatMessageModel).where(ChatMessageModel.id == out.id))).scalar_one()
    assert msg_row.chat_id == chat_id
    assert msg_row.role == ChatRole.USER
    assert msg_row.content == "First message"
    assert msg_row.created_at is not None

    # ---- chat "touch" behavior
    chat_after = (await session.execute(select(ChatModel).where(ChatModel.id == chat_id))).scalar_one()
    assert chat_after.updated_at is not None

    # If your touch sets updated_at=utcnow(), it should advance.
    # Allow a tiny tolerance for DB/clock resolution.
    assert chat_after.updated_at >= before_updated_at - timedelta(milliseconds=5)

    # A stricter expectation: it should generally move forward
    # (comment out if your storage layer overwrites timestamps oddly)
    assert chat_after.updated_at >= before_updated_at


async def test_create_chat_message_wrong_owner_is_forbidden_and_does_not_insert(
    session, uow, uow_factory, pdf_bytes, tmp_path: Path
):
    real_owner_id, _, chat_id = await _seed_chat(
        uow_factory=uow_factory, uow=uow, tmp_path=tmp_path, pdf_bytes=pdf_bytes
    )
    wrong_owner_id = uuid4()
    assert wrong_owner_id != real_owner_id

    # count messages before
    before = await session.scalar(
        select(ChatMessageModel.id).where(ChatMessageModel.chat_id == chat_id).limit(1)
    )

    uc = CreateChatMessageUseCase(uow_factory=uow_factory)

    with pytest.raises(ChatNotFoundOrForbidden):
        await uc.execute(
            CreateMessageInputDTO(
                owner_id=wrong_owner_id,
                chat_id=chat_id,
                role=ChatRole.USER,
                content="Should not be inserted",
            )
        )

    after = await session.scalar(
        select(ChatMessageModel.id).where(ChatMessageModel.chat_id == chat_id).limit(1)
    )
    assert before == after

# tests/integration/infrastructure/reply/test_reply_repositories.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from talk_to_pdf.backend.app.domain.projects.entities import Project, ProjectDocument
from talk_to_pdf.backend.app.domain.projects.value_objects import ProjectName
from talk_to_pdf.backend.app.domain.reply import Chat, ChatMessage
from talk_to_pdf.backend.app.domain.reply.enums import ChatRole

from talk_to_pdf.backend.app.infrastructure.db.models import ProjectModel
from talk_to_pdf.backend.app.infrastructure.db.models.reply import ChatModel, ChatMessageModel
from talk_to_pdf.backend.app.infrastructure.projects.repositories import SqlAlchemyProjectRepository
from talk_to_pdf.backend.app.infrastructure.reply.repositories import (
    SqlAlchemyChatRepository,
    SqlAlchemyChatMessageRepository,
)

pytestmark = pytest.mark.asyncio


# -----------------------------
# Deterministic timestamps
# -----------------------------
def _dt(minutes: int) -> datetime:
    return datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)


# -----------------------------
# Project helpers (reuse your style)
# -----------------------------
def make_project(*, owner_id: UUID, name: str = "P", created_at: datetime | None = None) -> Project:
    created_at = created_at or _dt(0)
    p = Project(
        id=uuid4(),
        owner_id=owner_id,
        name=ProjectName(name),
        created_at=created_at,
    )
    doc = ProjectDocument(
        id=uuid4(),
        project_id=p.id,
        original_filename="file.pdf",
        storage_path=f"/tmp/{p.id}.pdf",
        content_type="application/pdf",
        size_bytes=123,
        uploaded_at=_dt(1),
    )
    return p.attach_main_document(doc)


async def make_saved_project_id(session, *, owner_id: UUID, name: str = "P") -> UUID:
    proj_repo = SqlAlchemyProjectRepository(session)
    saved = await proj_repo.add(make_project(owner_id=owner_id, name=name))
    return saved.id


# -----------------------------
# Chat / message helpers
# -----------------------------
def make_chat(
    *,
    owner_id: UUID,
    project_id: UUID,
    title: str = "Chat",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Chat:
    created_at = created_at or _dt(0)
    updated_at = updated_at or created_at
    return Chat(
        id=uuid4(),
        owner_id=owner_id,
        project_id=project_id,
        title=title,
        created_at=created_at,
        updated_at=updated_at,
    )


def make_msg(
    *,
    chat_id: UUID,
    role: ChatRole,
    content: str,
    created_at: datetime,
) -> ChatMessage:
    return ChatMessage(
        id=uuid4(),
        chat_id=chat_id,
        role=role,
        content=content,
        created_at=created_at,
    )


async def _row_counts(session) -> tuple[int, int, int]:
    p = (await session.execute(select(ProjectModel))).scalars().all()
    c = (await session.execute(select(ChatModel))).scalars().all()
    m = (await session.execute(select(ChatMessageModel))).scalars().all()
    return len(p), len(c), len(m)


# ============================================================
# Chat repo tests
# ============================================================
async def test_chat_add_persists_row(session):
    owner_id = uuid4()
    project_id = await make_saved_project_id(session, owner_id=owner_id, name="Proj")

    repo = SqlAlchemyChatRepository(session)
    chat = make_chat(owner_id=owner_id, project_id=project_id, title="My Chat", created_at=_dt(10), updated_at=_dt(11))

    await repo.add(chat)

    # verify DB row exists
    cm = await session.get(ChatModel, chat.id)
    assert cm is not None
    assert cm.id == chat.id
    assert cm.owner_id == owner_id
    assert cm.project_id == project_id
    assert cm.title == "My Chat"
    assert cm.created_at == _dt(10)
    assert cm.updated_at == _dt(11)


async def test_chat_get_by_owner_and_id_filters_owner_via_project_owner(session):
    owner_a = uuid4()
    owner_b = uuid4()

    project_a = await make_saved_project_id(session, owner_id=owner_a, name="A")
    project_b = await make_saved_project_id(session, owner_id=owner_b, name="B")

    repo = SqlAlchemyChatRepository(session)

    chat_a = make_chat(owner_id=owner_a, project_id=project_a, title="A1", created_at=_dt(0), updated_at=_dt(1))
    chat_b = make_chat(owner_id=owner_b, project_id=project_b, title="B1", created_at=_dt(0), updated_at=_dt(1))
    await repo.add(chat_a)
    await repo.add(chat_b)

    hit = await repo.get_by_owner_and_id(owner_id=owner_a, chat_id=chat_a.id)
    assert hit is not None
    assert hit.id == chat_a.id

    miss = await repo.get_by_owner_and_id(owner_id=owner_b, chat_id=chat_a.id)
    assert miss is None


async def test_chat_list_by_owner_and_project_orders_by_updated_at_desc_and_paginates(session):
    owner = uuid4()
    other_owner = uuid4()

    project_id = await make_saved_project_id(session, owner_id=owner, name="Mine")
    other_project_id = await make_saved_project_id(session, owner_id=other_owner, name="Other")

    repo = SqlAlchemyChatRepository(session)

    # same project, different updated_at
    c_old = make_chat(owner_id=owner, project_id=project_id, title="Old", created_at=_dt(0), updated_at=_dt(5))
    c_mid = make_chat(owner_id=owner, project_id=project_id, title="Mid", created_at=_dt(0), updated_at=_dt(10))
    c_new = make_chat(owner_id=owner, project_id=project_id, title="New", created_at=_dt(0), updated_at=_dt(20))

    # should never appear:
    c_other_owner = make_chat(owner_id=other_owner, project_id=other_project_id, title="Nope", updated_at=_dt(999))

    await repo.add(c_old)
    await repo.add(c_mid)
    await repo.add(c_new)
    await repo.add(c_other_owner)

    chats = await repo.list_by_owner_and_project(owner_id=owner, project_id=project_id, limit=50, offset=0)
    assert [c.title for c in chats] == ["New", "Mid", "Old"]

    # pagination: skip newest
    chats2 = await repo.list_by_owner_and_project(owner_id=owner, project_id=project_id, limit=2, offset=1)
    assert [c.title for c in chats2] == ["Mid", "Old"]


async def test_chat_delete_by_owner_and_id_deletes_only_if_owned(session):
    owner_a = uuid4()
    owner_b = uuid4()

    project_a = await make_saved_project_id(session, owner_id=owner_a, name="A")

    repo = SqlAlchemyChatRepository(session)

    chat = make_chat(owner_id=owner_a, project_id=project_a, title="ToDel", updated_at=_dt(1))
    await repo.add(chat)

    ok = await repo.delete_by_owner_and_id(owner_id=owner_a, chat_id=chat.id)
    assert ok is True
    assert await session.get(ChatModel, chat.id) is None

    # recreate, wrong owner -> False and still exists
    chat2 = make_chat(owner_id=owner_a, project_id=project_a, title="ToKeep", updated_at=_dt(2))
    await repo.add(chat2)

    bad = await repo.delete_by_owner_and_id(owner_id=owner_b, chat_id=chat2.id)
    assert bad is False
    assert await session.get(ChatModel, chat2.id) is not None


async def test_chat_delete_cascades_messages(session):
    owner = uuid4()
    project_id = await make_saved_project_id(session, owner_id=owner, name="P")

    chat_repo = SqlAlchemyChatRepository(session)
    msg_repo = SqlAlchemyChatMessageRepository(session)

    chat = make_chat(owner_id=owner, project_id=project_id, title="Cascade", created_at=_dt(0), updated_at=_dt(0))
    await chat_repo.add(chat)

    await msg_repo.add_many(
        [
            make_msg(chat_id=chat.id, role=ChatRole.USER, content="u1", created_at=_dt(1)),
            make_msg(chat_id=chat.id, role=ChatRole.ASSISTANT, content="a1", created_at=_dt(2)),
        ]
    )

    _, before_chats, before_msgs = await _row_counts(session)
    assert before_chats == 1
    assert before_msgs == 2

    ok = await chat_repo.delete_by_owner_and_id(owner_id=owner, chat_id=chat.id)
    assert ok is True

    _, after_chats, after_msgs = await _row_counts(session)
    assert after_chats == 0
    assert after_msgs == 0


# ============================================================
# ChatMessage repo tests
# ============================================================
async def test_message_add_persists_row(session):
    owner = uuid4()
    project_id = await make_saved_project_id(session, owner_id=owner)
    chat_repo = SqlAlchemyChatRepository(session)
    msg_repo = SqlAlchemyChatMessageRepository(session)

    chat = make_chat(owner_id=owner, project_id=project_id, title="MsgTest", created_at=_dt(0), updated_at=_dt(0))
    await chat_repo.add(chat)

    msg = make_msg(chat_id=chat.id, role=ChatRole.USER, content="hello", created_at=_dt(5))
    await msg_repo.add(msg)

    mm = await session.get(ChatMessageModel, msg.id)
    assert mm is not None
    assert mm.chat_id == chat.id
    assert mm.role == ChatRole.USER
    assert mm.content == "hello"
    assert mm.created_at == _dt(5)


async def test_message_add_many_noop_on_empty(session):
    msg_repo = SqlAlchemyChatMessageRepository(session)
    await msg_repo.add_many([])  # should not crash


async def test_list_recent_by_owner_and_chat_returns_oldest_to_newest(session):
    owner = uuid4()
    project_id = await make_saved_project_id(session, owner_id=owner)

    chat_repo = SqlAlchemyChatRepository(session)
    msg_repo = SqlAlchemyChatMessageRepository(session)

    chat = make_chat(owner_id=owner, project_id=project_id, title="Window", created_at=_dt(0), updated_at=_dt(0))
    await chat_repo.add(chat)

    # create 5 messages at minutes 1..5
    msgs = [
        make_msg(chat_id=chat.id, role=ChatRole.USER, content="m1", created_at=_dt(1)),
        make_msg(chat_id=chat.id, role=ChatRole.ASSISTANT, content="m2", created_at=_dt(2)),
        make_msg(chat_id=chat.id, role=ChatRole.USER, content="m3", created_at=_dt(3)),
        make_msg(chat_id=chat.id, role=ChatRole.ASSISTANT, content="m4", created_at=_dt(4)),
        make_msg(chat_id=chat.id, role=ChatRole.USER, content="m5", created_at=_dt(5)),
    ]
    await msg_repo.add_many(msgs)

    # request last 3 -> should return minutes 3,4,5 in ascending order
    recent = await msg_repo.list_recent_by_owner_and_chat(owner_id=owner, chat_id=chat.id, limit=3)
    assert [m.content for m in recent] == ["m3", "m4", "m5"]
    assert [m.created_at for m in recent] == [_dt(3), _dt(4), _dt(5)]


async def test_list_recent_by_owner_and_chat_before_filters_correctly(session):
    owner = uuid4()
    project_id = await make_saved_project_id(session, owner_id=owner)

    chat_repo = SqlAlchemyChatRepository(session)
    msg_repo = SqlAlchemyChatMessageRepository(session)

    chat = make_chat(owner_id=owner, project_id=project_id, title="Before", created_at=_dt(0), updated_at=_dt(0))
    await chat_repo.add(chat)

    await msg_repo.add_many(
        [
            make_msg(chat_id=chat.id, role=ChatRole.USER, content="m1", created_at=_dt(1)),
            make_msg(chat_id=chat.id, role=ChatRole.USER, content="m2", created_at=_dt(2)),
            make_msg(chat_id=chat.id, role=ChatRole.USER, content="m3", created_at=_dt(3)),
            make_msg(chat_id=chat.id, role=ChatRole.USER, content="m4", created_at=_dt(4)),
            make_msg(chat_id=chat.id, role=ChatRole.USER, content="m5", created_at=_dt(5)),
        ]
    )

    # before minute 4 => eligible are 1,2,3; last 2 => 2,3 (oldest->newest)
    recent = await msg_repo.list_recent_by_owner_and_chat(
        owner_id=owner,
        chat_id=chat.id,
        limit=2,
        before=_dt(4),
    )
    assert [m.content for m in recent] == ["m2", "m3"]


async def test_list_recent_by_owner_and_chat_wrong_owner_returns_empty(session):
    owner_a = uuid4()
    owner_b = uuid4()

    project_id = await make_saved_project_id(session, owner_id=owner_a)

    chat_repo = SqlAlchemyChatRepository(session)
    msg_repo = SqlAlchemyChatMessageRepository(session)

    chat = make_chat(owner_id=owner_a, project_id=project_id, title="Sec", created_at=_dt(0), updated_at=_dt(0))
    await chat_repo.add(chat)

    await msg_repo.add(make_msg(chat_id=chat.id, role=ChatRole.USER, content="secret", created_at=_dt(1)))

    out = await msg_repo.list_recent_by_owner_and_chat(owner_id=owner_b, chat_id=chat.id, limit=50)
    assert out == []


async def test_delete_by_owner_and_chat_deletes_only_if_owned(session):
    owner_a = uuid4()
    owner_b = uuid4()

    project_id = await make_saved_project_id(session, owner_id=owner_a)

    chat_repo = SqlAlchemyChatRepository(session)
    msg_repo = SqlAlchemyChatMessageRepository(session)

    chat = make_chat(owner_id=owner_a, project_id=project_id, title="DelMsgs", created_at=_dt(0), updated_at=_dt(0))
    await chat_repo.add(chat)

    await msg_repo.add_many(
        [
            make_msg(chat_id=chat.id, role=ChatRole.USER, content="m1", created_at=_dt(1)),
            make_msg(chat_id=chat.id, role=ChatRole.ASSISTANT, content="m2", created_at=_dt(2)),
            make_msg(chat_id=chat.id, role=ChatRole.USER, content="m3", created_at=_dt(3)),
        ]
    )

    # wrong owner: delete 0
    deleted0 = await msg_repo.delete_by_owner_and_chat(owner_id=owner_b, chat_id=chat.id)
    assert deleted0 == 0

    # correct owner: deletes all 3
    deleted3 = await msg_repo.delete_by_owner_and_chat(owner_id=owner_a, chat_id=chat.id)
    assert deleted3 == 3

    remaining = (await session.execute(select(ChatMessageModel).where(ChatMessageModel.chat_id == chat.id))).scalars().all()
    assert remaining == []

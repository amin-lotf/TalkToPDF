from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from talk_to_pdf.backend.app.domain.projects.entities import Project, ProjectDocument
from talk_to_pdf.backend.app.domain.projects.value_objects import ProjectName
from talk_to_pdf.backend.app.infrastructure.db.models.project import ProjectModel, ProjectDocumentModel
from talk_to_pdf.backend.app.infrastructure.projects.repositories import SqlAlchemyProjectRepository

pytestmark = pytest.mark.asyncio


def _dt(minutes: int) -> datetime:
    # deterministic timestamps for ordering checks
    return datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)


def make_project(*, owner_id=None, name="Project A", created_at=None) -> Project:
    owner_id = owner_id or uuid4()
    created_at = created_at or _dt(0)
    p = Project(
        id=uuid4(),
        owner_id=owner_id,
        name=ProjectName(name),
        created_at=created_at,
    )
    doc = ProjectDocument(
        id=uuid4(),
        project_id=p.id,  # will be re-wired by repo.add() anyway, but keep consistent
        original_filename="file.pdf",
        storage_path=f"/tmp/{p.id}.pdf",
        content_type="application/pdf",
        size_bytes=123,
        uploaded_at=_dt(1),
    )
    return p.attach_main_document(doc)


async def _row_counts(session) -> tuple[int, int]:
    p = (await session.execute(select(ProjectModel))).scalars().all()
    d = (await session.execute(select(ProjectDocumentModel))).scalars().all()
    return len(p), len(d)


async def test_add_persists_project_and_document_and_returns_hydrated(session):
    repo = SqlAlchemyProjectRepository(session)

    project = make_project(name="My Project")
    saved = await repo.add(project)

    assert saved.id == project.id
    assert saved.owner_id == project.owner_id
    assert saved.name.value == "My Project"
    assert saved.primary_document is not None

    # ensure the cycle wiring is correct
    assert saved.primary_document.project_id == saved.id

    # verify DB rows exist
    pm = await session.get(ProjectModel, saved.id)
    assert pm is not None
    assert pm.name == "My Project"
    assert pm.primary_document_id == saved.primary_document.id

    dm = await session.get(ProjectDocumentModel, saved.primary_document.id)
    assert dm is not None
    assert dm.project_id == saved.id
    assert dm.storage_path == saved.primary_document.storage_path


async def test_add_raises_if_primary_document_missing(session):
    repo = SqlAlchemyProjectRepository(session)

    p = Project(
        id=uuid4(),
        owner_id=uuid4(),
        name=ProjectName("No Doc"),
        created_at=_dt(0),
        primary_document=None,
    )

    with pytest.raises(ValueError, match="primary_document"):
        await repo.add(p)


async def test_get_by_id_round_trip(session):
    repo = SqlAlchemyProjectRepository(session)

    project = make_project(name="Round Trip")
    saved = await repo.add(project)

    loaded = await repo.get_by_id(saved.id)
    assert loaded is not None
    assert loaded.id == saved.id
    assert loaded.owner_id == saved.owner_id
    assert loaded.name.value == "Round Trip"
    assert loaded.primary_document is not None
    assert loaded.primary_document.id == saved.primary_document.id


async def test_get_by_id_returns_none_when_missing(session):
    repo = SqlAlchemyProjectRepository(session)

    missing = await repo.get_by_id(uuid4())
    assert missing is None


async def test_get_by_owner_and_id_filters_owner(session):
    repo = SqlAlchemyProjectRepository(session)

    owner_a = uuid4()
    owner_b = uuid4()

    proj_a = make_project(owner_id=owner_a, name="A")
    saved_a = await repo.add(proj_a)

    # correct owner -> found
    hit = await repo.get_by_owner_and_id(owner_a, saved_a.id)
    assert hit is not None
    assert hit.id == saved_a.id

    # wrong owner -> None
    miss = await repo.get_by_owner_and_id(owner_b, saved_a.id)
    assert miss is None


async def test_list_by_owner_orders_by_created_at_desc(session):
    repo = SqlAlchemyProjectRepository(session)

    owner = uuid4()

    p1 = make_project(owner_id=owner, name="Old", created_at=_dt(0))
    p2 = make_project(owner_id=owner, name="New", created_at=_dt(10))
    p3 = make_project(owner_id=uuid4(), name="OtherOwner", created_at=_dt(20))  # should not appear

    await repo.add(p1)
    await repo.add(p2)
    await repo.add(p3)

    projects = await repo.list_by_owner(owner)
    assert [p.name.value for p in projects] == ["New", "Old"]


async def test_rename_updates_name_and_returns_hydrated(session):
    repo = SqlAlchemyProjectRepository(session)

    project = make_project(name="Before")
    saved = await repo.add(project)

    saved.rename(ProjectName("After"))
    renamed = await repo.rename(saved)

    assert renamed.id == saved.id
    assert renamed.name.value == "After"
    assert renamed.primary_document is not None

    # verify DB actually changed
    pm = await session.get(ProjectModel, saved.id)
    assert pm is not None
    assert pm.name == "After"


async def test_rename_raises_if_project_not_found(session):
    repo = SqlAlchemyProjectRepository(session)

    project = make_project(name="Ghost")
    # don't add; try rename directly
    with pytest.raises(ValueError, match="not found"):
        await repo.rename(project)


async def test_delete_removes_project_and_cascades_document(session):
    repo = SqlAlchemyProjectRepository(session)

    project = make_project(name="To Delete")
    saved = await repo.add(project)

    before_p, before_d = await _row_counts(session)
    assert before_p == 1
    assert before_d == 1

    await repo.delete(saved.id)

    # after flush, rows should be gone
    after_p, after_d = await _row_counts(session)
    assert after_p == 0
    assert after_d == 0

    assert await repo.get_by_id(saved.id) is None

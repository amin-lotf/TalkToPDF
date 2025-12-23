from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO
from talk_to_pdf.backend.app.application.projects.use_cases.create_project import CreateProjectUseCase
from talk_to_pdf.backend.app.domain.files.interfaces import StoredFileInfo
from talk_to_pdf.backend.app.domain.files.errors import FailedToSaveFile
from talk_to_pdf.backend.app.domain.projects.errors import FailedToCreateProject
from talk_to_pdf.backend.app.infrastructure.db.models.project import ProjectModel, ProjectDocumentModel


pytestmark = pytest.mark.asyncio


# ---------------------------
# Test doubles (FileStorage)
# ---------------------------

@dataclass
class SpyFileStorage:
    stored: Optional[StoredFileInfo] = None
    save_called: bool = False
    delete_called: bool = False
    deleted_path: Optional[str] = None

    async def save(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> StoredFileInfo:
        self.save_called = True
        # deterministic path for assertions
        self.stored = StoredFileInfo(
            original_filename=filename,
            stored_filename="stored.pdf",
            storage_path=f"{owner_id}/{project_id}/stored.pdf",
            size_bytes=len(content),
            content_type=content_type,
        )
        return self.stored

    async def delete(self, path: str) -> None:
        self.delete_called = True
        self.deleted_path = path


class FailingSaveFileStorage(SpyFileStorage):
    async def save(self, **kwargs) -> StoredFileInfo:  # type: ignore[override]
        raise RuntimeError("disk full")


# ---------------------------
# Helpers
# ---------------------------

async def _fetch_project_rows(session, project_id: UUID):
    pm = await session.get(ProjectModel, project_id)
    if pm is None:
        return None, None
    dm = await session.get(ProjectDocumentModel, pm.primary_document_id)
    return pm, dm


# ---------------------------
# Tests
# ---------------------------

async def test_create_project_success_persists_project_and_document(uow, session):
    file_storage = SpyFileStorage()
    use_case = CreateProjectUseCase(uow=uow, file_storage=file_storage)

    owner_id = uuid4()
    dto = CreateProjectInputDTO(
        owner_id=owner_id,
        name="My Project",
        file_bytes=b"%PDF-1.4 fake pdf bytes",
        filename="my.pdf",
        content_type="application/pdf",
    )

    out = await use_case.execute(dto)

    # returned DTO
    assert out.owner_id == owner_id
    assert out.name == "My Project"
    assert out.primary_document.original_filename == "my.pdf"
    assert out.primary_document.content_type == "application/pdf"
    assert out.primary_document.size_bytes == len(dto.file_bytes)

    # file storage was used
    assert file_storage.save_called is True
    assert file_storage.stored is not None
    assert out.primary_document.storage_path == file_storage.stored.storage_path

    # DB persisted
    pm, dm = await _fetch_project_rows(session, out.id)
    assert pm is not None
    assert pm.owner_id == owner_id
    assert pm.name == "My Project"
    assert dm is not None
    assert dm.project_id == out.id
    assert dm.storage_path == file_storage.stored.storage_path
    assert dm.original_filename == "my.pdf"


async def test_create_project_raises_failed_to_save_file_and_does_not_touch_db(uow, session):
    file_storage = FailingSaveFileStorage()
    use_case = CreateProjectUseCase(uow=uow, file_storage=file_storage)

    dto = CreateProjectInputDTO(
        owner_id=uuid4(),
        name="Will Fail",
        file_bytes=b"whatever",
        filename="x.pdf",
        content_type="application/pdf",
    )

    with pytest.raises(FailedToSaveFile):
        await use_case.execute(dto)

    # No rows should be created at all
    projects = (await session.execute(select(ProjectModel))).scalars().all()
    docs = (await session.execute(select(ProjectDocumentModel))).scalars().all()
    assert projects == []
    assert docs == []


async def test_create_project_db_failure_deletes_saved_file_and_raises(uow, session, monkeypatch):
    """
    Simulate repo.add() throwing to force the cleanup path:
    - file_storage.save succeeds
    - uow.project_repo.add raises
    - file_storage.delete is called with stored.storage_path
    - FailedToCreateProject is raised
    """
    file_storage = SpyFileStorage()
    use_case = CreateProjectUseCase(uow=uow, file_storage=file_storage)

    dto = CreateProjectInputDTO(
        owner_id=uuid4(),
        name="DB Fails",
        file_bytes=b"pdfbytes",
        filename="y.pdf",
        content_type="application/pdf",
    )

    # patch the concrete repo instance inside uow to fail on add
    async def _boom_add(project):
        raise RuntimeError("db down")

    monkeypatch.setattr(uow.project_repo, "add", _boom_add)

    with pytest.raises(FailedToCreateProject):
        await use_case.execute(dto)

    # cleanup happened
    assert file_storage.save_called is True
    assert file_storage.stored is not None
    assert file_storage.delete_called is True
    assert file_storage.deleted_path == file_storage.stored.storage_path

    # and nothing persisted
    projects = (await session.execute(select(ProjectModel))).scalars().all()
    docs = (await session.execute(select(ProjectDocumentModel))).scalars().all()
    assert projects == []
    assert docs == []

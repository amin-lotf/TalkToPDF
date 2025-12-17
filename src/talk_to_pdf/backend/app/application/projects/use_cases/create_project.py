from __future__ import annotations

from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO, ProjectDTO
from talk_to_pdf.backend.app.application.projects.mappers import (
    build_project_with_main_document,
    project_domain_to_output_dto,
    project_input_dto_to_domain,
)
from talk_to_pdf.backend.app.domain.files.errors import FailedToSaveFile
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.projects.errors import FailedToCreateProject
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork


class CreateProjectUseCase:
    def __init__(self, uow: UnitOfWork, file_storage: FileStorage) -> None:
        self._uow = uow
        self._file_storage = file_storage

    async def execute(self, dto: CreateProjectInputDTO) -> ProjectDTO:
        async with self._uow:
            project = project_input_dto_to_domain(dto)

            # 1) Save the file first
            try:
                stored = await self._file_storage.save(
                    owner_id=dto.owner_id,
                    project_id=project.id,
                    filename=dto.filename,
                    content=dto.file_bytes,
                    content_type=dto.content_type,
                )
            except Exception as e:
                # file save failed, nothing to clean up
                raise FailedToSaveFile("Could not save uploaded file") from e

            # 2) Build domain object with main document
            project = build_project_with_main_document(project=project, stored=stored)

            # 3) Persist project + document (single DB transaction; commit handled by UoW)
            try:
                saved = await self._uow.project_repo.add(project)
            except Exception:
                # DB failed -> cleanup the file, then re-raise original DB error
                try:
                    await self._file_storage.delete(stored.storage_path)
                except Exception:
                    pass
                raise FailedToCreateProject(project.name.value)

            return project_domain_to_output_dto(saved)

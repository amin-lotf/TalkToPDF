from __future__ import annotations

from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO, ProjectDTO
from talk_to_pdf.backend.app.application.projects.mappers import (
    project_domain_to_output_dto,
    build_project_with_main_document,
    project_input_dto_to_domain,
)
from talk_to_pdf.backend.app.domain.files.errors import FailedToSaveFile
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.projects import ProjectRepository


class CreateProjectUseCase:
    def __init__(self, project_repo: ProjectRepository, file_storage: FileStorage) -> None:
        self._project_repo = project_repo
        self._file_storage = file_storage

    async def execute(self, dto: CreateProjectInputDTO) -> ProjectDTO:
        project = project_input_dto_to_domain(dto)

        # 1) Save the file first
        try:
            stored = await self._file_storage.save(
                owner_id=dto.owner_id,          # NOTE: owner_id (your code had a typo ower_id)
                project_id=project.id,
                filename=dto.filename,          # keep naming consistent with your FileStorage interface
                content=dto.file_bytes,
                content_type=dto.content_type,
            )
        except Exception as e:
            # file save failed, nothing to clean up
            raise FailedToSaveFile("Could not save uploaded file") from e

        # 2) Build domain object with main document
        project = build_project_with_main_document(project=project, stored=stored)

        # 3) Persist project + document (single DB transaction; commit handled by UoW/session)
        try:
            saved = await self._project_repo.add(project)
        except Exception as e:
            # DB failed -> cleanup the file
            try:
                await self._file_storage.delete(stored.storage_path)  # or stored.path if that's your field
            except Exception:
                # Don't hide the original DB failure
                pass
            raise  # re-raise original DB error for correct debugging

        return project_domain_to_output_dto(saved)

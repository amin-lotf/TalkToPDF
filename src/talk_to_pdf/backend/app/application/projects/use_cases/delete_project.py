from __future__ import annotations
from talk_to_pdf.backend.app.application.projects.dto import DeleteProjectInputDTO
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.projects import ProjectRepository
from talk_to_pdf.backend.app.domain.projects.errors import ProjectNotFound, FailedToDeleteProject, \
    FailedToDeleteProjectDocument
from talk_to_pdf.backend.app.infrastructure.db.uow import UnitOfWork


class DeleteProjectUseCase:
    def __init__(self, uow: UnitOfWork, file_storage: FileStorage) -> None:
        self._uow = uow
        self._file_storage = file_storage

    async def execute(self, dto: DeleteProjectInputDTO) -> None:
        async with self._uow:
            project = await self._uow.project_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                project_id=dto.project_id
            )
            if not project:
                raise ProjectNotFound(project_id=str(dto.project_id))
            try:
                await self._file_storage.delete(project.primary_document.storage_path)
            except Exception:
                raise FailedToDeleteProjectDocument(project.name.value)
            try:
                project_id = dto.project_id
                await self._uow.project_repo.delete(project_id)
            except Exception:
                raise FailedToDeleteProject(project.name.value)

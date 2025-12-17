from __future__ import annotations
from talk_to_pdf.backend.app.application.projects.dto import (
    RenameProjectInputDTO,
    ProjectDTO,
)
from talk_to_pdf.backend.app.application.projects.mappers import (
    project_domain_to_output_dto,
)
from talk_to_pdf.backend.app.domain.projects.errors import ProjectNotFound, FailedToRenameProject
from talk_to_pdf.backend.app.domain.projects.value_objects import  ProjectName
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork


class RenameProjectUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, dto: RenameProjectInputDTO) -> ProjectDTO:
        async with self._uow:
            project = await self._uow.project_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                project_id=dto.project_id
            )
            if not project:
                raise ProjectNotFound(project_id=str(dto.project_id))
            project.rename(ProjectName(dto.new_name))
            try:
                saved = await self._uow.project_repo.rename(project=project)
            except Exception:
                raise FailedToRenameProject()

            return project_domain_to_output_dto(saved)

from __future__ import annotations
from talk_to_pdf.backend.app.application.projects.dto import (
    RenameProjectInputDTO,
    ProjectDTO,
)
from talk_to_pdf.backend.app.application.projects.mappers import (
    project_domain_to_output_dto,
)
from talk_to_pdf.backend.app.domain.projects import ProjectRepository
from talk_to_pdf.backend.app.domain.projects.errors import ProjectNotFound
from talk_to_pdf.backend.app.domain.projects.value_objects import  ProjectName


class RenameProjectUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
    ) -> None:
        self._project_repo: ProjectRepository = project_repo

    async def execute(self, dto: RenameProjectInputDTO) -> ProjectDTO:
        project_id = dto.project_id
        project = await self._project_repo.get_by_id(project_id)
        if project is None:
            raise ProjectNotFound("Project not found.")
        project.rename(ProjectName(dto.new_name))
        saved = await self._project_repo.add(project)
        return project_domain_to_output_dto(saved)

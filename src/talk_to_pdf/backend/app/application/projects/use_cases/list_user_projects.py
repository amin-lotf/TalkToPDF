# talk_to_pdf/backend/app/application/projects/use_cases/list_user_projects.py
from __future__ import annotations

from typing import List

from talk_to_pdf.backend.app.application.projects.dto import (
    ListProjectsInputDTO,
    ProjectDTO,
)
from talk_to_pdf.backend.app.application.projects.mappers import (
    project_domain_to_output_dto,
)
from talk_to_pdf.backend.app.domain.projects import ProjectRepository


class ListUserProjectsUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
    ) -> None:
        self._project_repo: ProjectRepository = project_repo

    async def execute(self, dto: ListProjectsInputDTO) -> List[ProjectDTO]:
        owner_id = dto.owner_id
        projects = await self._project_repo.list_by_owner(owner_id)
        return [project_domain_to_output_dto(p) for p in projects]

from __future__ import annotations
from talk_to_pdf.backend.app.application.projects.dto import DeleteProjectInputDTO
from talk_to_pdf.backend.app.domain.projects import ProjectRepository


class DeleteProjectUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
    ) -> None:
        self._project_repo: ProjectRepository = project_repo

    async def execute(self, dto: DeleteProjectInputDTO) -> None:
        project_id = dto.project_id
        await self._project_repo.delete(project_id)

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
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.projects import ProjectRepository
from talk_to_pdf.backend.app.infrastructure.db.uow import UnitOfWork


class ListUserProjectsUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, dto: ListProjectsInputDTO) -> List[ProjectDTO]:
        async with self._uow:
            owner_id = dto.owner_id
            projects = await self._uow.project_repo.list_by_owner(owner_id)
            return [project_domain_to_output_dto(p) for p in projects]

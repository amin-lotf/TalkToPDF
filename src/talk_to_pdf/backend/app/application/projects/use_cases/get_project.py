from talk_to_pdf.backend.app.application.projects.dto import GetProjectInputDTO, ProjectDTO
from talk_to_pdf.backend.app.application.projects.mappers import project_domain_to_output_dto
from talk_to_pdf.backend.app.domain.projects.errors import ProjectNotFound
from talk_to_pdf.backend.app.infrastructure.db.uow import UnitOfWork


class GetProjectUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, dto: GetProjectInputDTO) -> ProjectDTO:
        async with self._uow:
            project = await self._uow.project_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                project_id=dto.project_id
            )
            if not project:
                raise ProjectNotFound(project_id=str(dto.project_id))
            return project_domain_to_output_dto(project)
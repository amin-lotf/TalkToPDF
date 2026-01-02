from talk_to_pdf.backend.app.application.indexing.dto import GetLatestIndexStatusInputDTO, IndexStatusDTO
from talk_to_pdf.backend.app.application.indexing.mappers import to_index_status_dto
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.indexing.errors import NoIndexesForProject


class GetLatestIndexStatusUseCase:
    """
    Fetch the latest status for a project (whatever the most recent index run is).
    Useful for a 'project status' endpoint.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, dto: GetLatestIndexStatusInputDTO) -> IndexStatusDTO:
        async with self._uow:
            index = await self._uow.index_repo.get_latest_by_project(project_id=dto.project_id)
            if not index:
                raise NoIndexesForProject(project_id=str(dto.project_id))
            return to_index_status_dto(index)
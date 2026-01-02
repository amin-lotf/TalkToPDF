from talk_to_pdf.backend.app.application.indexing.dto import GetIndexStatusByIdInputDTO, IndexStatusDTO
from talk_to_pdf.backend.app.application.indexing.mappers import to_index_status_dto
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.indexing.errors import IndexNotFound


class GetIndexStatusUseCase:
    """
    Fetch status for a specific index run by index_id.
    Best for UI polling once you have an index_id.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, dto: GetIndexStatusByIdInputDTO) -> IndexStatusDTO:
        async with self._uow:
            index = await self._uow.index_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                index_id=dto.index_id,
            )
            if not index:
                # Important: do NOT reveal whether it exists but belongs to someone else
                raise IndexNotFound(index_id=str(dto.index_id))

            return to_index_status_dto(index)



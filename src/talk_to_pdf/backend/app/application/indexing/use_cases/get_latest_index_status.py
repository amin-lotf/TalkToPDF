from talk_to_pdf.backend.app.application.indexing.dto import GetLatestIndexStatusInputDTO, IndexStatusDTO
from talk_to_pdf.backend.app.application.indexing.mappers import to_index_status_dto
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.indexing.errors import NoIndexesForProject
from talk_to_pdf.backend.app.domain.common.value_objects import EmbedConfig


class GetLatestIndexStatusUseCase:
    """
    Fetch the latest status for a project (whatever the most recent index run is).
    Useful for a 'project status' endpoint.
    """

    def __init__(self, uow: UnitOfWork,embed_config: EmbedConfig,) -> None:
        self._uow = uow
        self._embed_config = embed_config

    async def execute(self, dto: GetLatestIndexStatusInputDTO) -> IndexStatusDTO:
        async with self._uow:
            # First try to get a ready index (completed successfully) with matching embed signature
            index = await self._uow.index_repo.get_latest_ready_by_project_and_owner_and_signature(
                project_id=dto.project_id, owner_id=dto.owner_id, embed_signature=self._embed_config.signature())

            # If no ready index, check for active (in-progress) indexes with matching embed signature
            if not index:
                index = await self._uow.index_repo.get_latest_active_by_project_and_owner_and_signature(
                    project_id=dto.project_id, owner_id=dto.owner_id, embed_signature=self._embed_config.signature())

            if not index:
                raise NoIndexesForProject(project_id=str(dto.project_id))
            return to_index_status_dto(index)
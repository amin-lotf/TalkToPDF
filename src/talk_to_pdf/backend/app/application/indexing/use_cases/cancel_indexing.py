from talk_to_pdf.backend.app.application.indexing.dto import CancelIndexingInputDTO, IndexStatusDTO
from talk_to_pdf.backend.app.application.indexing.mappers import to_index_status_dto
from talk_to_pdf.backend.app.application.indexing.progress import report
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.errors import IndexNotFound


class CancelIndexingUseCase:
    """
    Request cancellation of an indexing run.

    Notes:
    - Idempotent: if cancel already requested, returns current status.
    - If run is already terminal, returns current status (no-op).
    - Sets a cancel flag in DB so the worker can stop gracefully.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, dto: CancelIndexingInputDTO) -> IndexStatusDTO:
        async with self._uow:
            index = await self._uow.index_repo.get_by_id(index_id=dto.index_id)
            if not index:
                raise IndexNotFound(index_id=str(dto.index_id))

            # Terminal states: cancellation is meaningless; return as-is.
            if index.status.is_terminal:
                return to_index_status_dto(index)

            # Idempotent: if already requested, return as-is.
            if index.cancel_requested:
                return to_index_status_dto(index)

            # Persist cancel request (worker should check this flag during processing)
            await self._uow.index_repo.request_cancel(index_id=dto.index_id)

            # Optional but useful: reflect in status/message quickly for UI.
            # This does NOT mean it's fully canceled yet—just requested.
            await report(
                uow=self._uow,
                index_id=dto.index_id,
                status=index.status,  # keep current (PENDING/RUNNING)
                progress=index.progress,
                message="Cancel requested",
                error=None,
                meta=None,
            )

            # Re-read for accurate DTO (cancel_requested flag)
            updated = await self._uow.index_repo.get_by_id(index_id=dto.index_id)
            # In case the repo returns an updated object directly in request_cancel, you could skip reread.
            if not updated:
                raise IndexNotFound(index_id=str(dto.index_id))

            return to_index_status_dto(updated)
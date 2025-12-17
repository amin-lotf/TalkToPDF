from __future__ import annotations
from talk_to_pdf.backend.app.application.indexing.dto import IndexStatusDTO, StartIndexingInputDTO
from talk_to_pdf.backend.app.application.indexing.interface import IndexingRunner
from talk_to_pdf.backend.app.application.indexing.mappers import to_index_status_dto
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.errors import FailedToStartIndexing
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork


class StartIndexingUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        runner: IndexingRunner,
        *,
        chunker_version: str,
        embedder_model: str,
        embedding_dim: int,
    ) -> None:
        self._uow = uow
        self._runner = runner
        self._chunker_version = chunker_version
        self._embedder_model = embedder_model
        self._embedding_dim = embedding_dim

    async def execute(self, dto: StartIndexingInputDTO) -> IndexStatusDTO:
        """
        Creates a new DocumentIndex row (PENDING) and enqueues the background job.

        Idempotency rule (simple):
        - If the latest index is active (PENDING/RUNNING), return it (don’t create a new one).
        - Otherwise create a new one.
        """
        async with self._uow:
            try:
                latest = await self._uow.index_repo.get_latest_by_project(project_id=dto.project_id)

                if latest and latest.status.is_active:
                    # Already running/queued -> return existing status
                    return to_index_status_dto(latest)

                created = await self._uow.index_repo.create_pending(
                    project_id=dto.project_id,
                    document_id=dto.document_id,
                    chunker_version=self._chunker_version,
                    embedder_model=self._embedder_model,
                    embedding_dim=self._embedding_dim,
                )
            except Exception as e:
                # If anything fails, keep exception surface clean
                raise FailedToStartIndexing("Could not start indexing") from e

        # Outside transaction: enqueue the worker
        try:
            await self._runner.enqueue(index_id=created.id)
        except Exception as e:
            # Optional: mark FAILED here (new small transaction) if enqueue fails.
            async with self._uow:
                await self._uow.index_repo.update_progress(
                    index_id=created.id,
                    status=IndexStatus.FAILED,
                    progress=0,
                    message="Failed to enqueue indexing job",
                    error=str(e),
                )
            raise FailedToStartIndexing("Index created but failed to enqueue job") from e
        return to_index_status_dto(created)

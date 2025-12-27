from __future__ import annotations

from dataclasses import asdict

from talk_to_pdf.backend.app.application.indexing.dto import IndexStatusDTO, StartIndexingInputDTO
from talk_to_pdf.backend.app.application.indexing.interfaces import IndexingRunner
from talk_to_pdf.backend.app.application.indexing.mappers import to_index_status_dto
from talk_to_pdf.backend.app.application.indexing.progress import report
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.errors import FailedToStartIndexing
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig
from talk_to_pdf.backend.app.domain.projects.errors import ProjectNotFound, DocumentNotFound


class StartIndexingUseCase:
    def __init__(
            self,
            uow: UnitOfWork,
            runner: IndexingRunner,
            *,
            chunker_version: str,
            embed_config: EmbedConfig
    ) -> None:
        self._uow = uow
        self._runner = runner
        self._chunker_version = chunker_version
        self._embed_config = embed_config

    async def execute(self, dto: StartIndexingInputDTO) -> IndexStatusDTO:
        """
        Creates a new DocumentIndex row (PENDING) and enqueues the background job.

        Idempotency rule (simple):
        - If the latest index is active (PENDING/RUNNING), return it (don’t create a new one).
        - Otherwise create a new one.
        """
        async with self._uow:
            try:
                latest = await self._uow.index_repo.get_latest_active_by_project_and_signature(
                    project_id=dto.project_id,
                    embed_signature=self._embed_config.signature()
                )

                if latest:
                    return to_index_status_dto(latest)
                project= await self._uow.project_repo.get_by_id(project_id=dto.project_id)
                if not project:
                    raise ProjectNotFound(project_id=str(dto.project_id))  # however you handle

                if project.primary_document.id != dto.document_id:
                    raise DocumentNotFound(document_id=str(dto.document_id))

                storage_path=project.primary_document.storage_path
                created = await self._uow.index_repo.create_pending(
                    project_id=dto.project_id,
                    document_id=dto.document_id,
                    storage_path=storage_path,
                    chunker_version=self._chunker_version,
                    embed_config=self._embed_config,
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
                    await report(
                        uow=self._uow,
                        index_id=created.id,
                        status=IndexStatus.FAILED,
                        message="Failed to enqueue indexing job",
                        error=str(e),
                    )
            raise FailedToStartIndexing("Index created but failed to enqueue job") from e
        return to_index_status_dto(created)

from typing import Annotated

from fastapi import Depends

from talk_to_pdf.backend.app.application.indexing.interfaces import IndexingRunner
from talk_to_pdf.backend.app.application.indexing.use_cases.cancel_indexing import CancelIndexingUseCase
from talk_to_pdf.backend.app.application.indexing.use_cases.get_index_status import GetIndexStatusUseCase
from talk_to_pdf.backend.app.application.indexing.use_cases.get_latest_index_status import GetLatestIndexStatusUseCase
from talk_to_pdf.backend.app.application.indexing.use_cases.start_indexing import StartIndexingUseCase
from talk_to_pdf.backend.app.core.config import settings
from talk_to_pdf.backend.app.core.deps import get_uow, get_indexing_runner, get_embed_config
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig


def get_chunker_version() -> str:
    return (
        f"{settings.CHUNKER_KIND}:"
        f"{settings.CHUNKER_MAX_CHARS}-{settings.CHUNKER_OVERLAP}"
    )


def get_start_indexing_use_case(
        uow: Annotated[UnitOfWork, Depends(get_uow)],
        indexing_runner: Annotated[IndexingRunner, Depends(get_indexing_runner)],
        embed_config: Annotated[EmbedConfig, Depends(get_embed_config)],
        chunker_version: Annotated[str, Depends(get_chunker_version)],
) -> StartIndexingUseCase:
    return StartIndexingUseCase(
        uow,
        indexing_runner,
        chunker_version=chunker_version,
        embed_config=embed_config
    )



def get_index_status_use_case(
        uow: Annotated[UnitOfWork, Depends(get_uow)],
)->GetIndexStatusUseCase:
    return GetIndexStatusUseCase(uow)


def get_latest_index_status_use_case(
        uow: Annotated[UnitOfWork, Depends(get_uow)],
        embed_config: Annotated[EmbedConfig, Depends(get_embed_config)],
)->GetLatestIndexStatusUseCase:
    return GetLatestIndexStatusUseCase(uow,embed_config=embed_config)

def get_cancel_indexing_use_case(
        uow: Annotated[UnitOfWork, Depends(get_uow)],
)->CancelIndexingUseCase:
    return CancelIndexingUseCase(uow)
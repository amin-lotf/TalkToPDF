from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator, Annotated, Callable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.application.indexing.interfaces import IndexingRunner
from talk_to_pdf.backend.app.core.config import settings
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.common.value_objects import EmbedConfig, ReplyGenerationConfig
from talk_to_pdf.backend.app.infrastructure.db.session import SessionLocal
from talk_to_pdf.backend.app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage
from talk_to_pdf.backend.app.infrastructure.indexing.runner_spawn import SpawnProcessIndexingRunner


async def get_session()->AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def get_uow(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[UnitOfWork]:
    # the transaction lifecycle (commit/rollback) is handled by UnitOfWork
    uow = SqlAlchemyUnitOfWork(session)
    yield uow

def get_uow_factory(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> Callable[[], UnitOfWork]:
    def _factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session)
    return _factory

@lru_cache
def get_indexing_runner()->IndexingRunner:
    return SpawnProcessIndexingRunner()


def get_embed_config()->EmbedConfig:
    return EmbedConfig(
        provider=settings.EMBED_PROVIDER,
        model=settings.EMBED_MODEL,
        batch_size=settings.EMBED_BATCH_SIZE,
        dimensions=settings.EMBED_DIMENSIONS,
    )

def get_reply_generation_config()->ReplyGenerationConfig:
    return ReplyGenerationConfig(
        provider=settings.REPLY_PROVIDER,
        model=settings.REPLY_MODEL,
        temperature=settings.REPLY_TEMPERATURE,
        max_output_tokens=settings.REPLY_MAX_OUTPUT_TOKENS,
        max_context_chars=settings.REPLY_MAX_CONTEXT_CHARS,
    )


@lru_cache
def get_file_storage() -> FileStorage:
    """
    Singleton file storage instance.
    Swap implementation here (FS / S3 / MinIO) without touching use cases.
    """
    base_dir = Path(settings.FILE_STORAGE_DIR)
    base_dir.mkdir(parents=True, exist_ok=True)
    return FilesystemFileStorage(base_dir)

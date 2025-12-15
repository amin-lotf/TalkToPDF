from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.core import settings
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.infrastructure.db.session import SessionLocal
from talk_to_pdf.backend.app.infrastructure.db.uow import UnitOfWork, SqlAlchemyUnitOfWork
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage


async def get_session()->AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def get_uow(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[UnitOfWork]:
    # the transaction lifecycle (commit/rollback) is handled by UnitOfWork
    uow = SqlAlchemyUnitOfWork(session)
    yield uow



@lru_cache
def get_file_storage() -> FileStorage:
    """
    Singleton file storage instance.
    Swap implementation here (FS / S3 / MinIO) without touching use cases.
    """
    base_dir = Path(settings.FILE_STORAGE_DIR)
    base_dir.mkdir(parents=True, exist_ok=True)
    return FilesystemFileStorage(base_dir)

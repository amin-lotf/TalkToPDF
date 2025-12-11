from typing import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from talk_to_pdf.backend.app.infrastructure.db import SessionLocal, UnitOfWork, SqlAlchemyUnitOfWork


async def get_session()->AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_uow(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[UnitOfWork]:
    # session lifecycle (commit/rollback) is handled in get_session
    uow = SqlAlchemyUnitOfWork(session)
    yield uow

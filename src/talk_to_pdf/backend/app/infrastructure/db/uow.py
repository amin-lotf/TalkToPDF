# app/infrastructure/db/uow.py
from typing import Protocol
from sqlalchemy.ext.asyncio import AsyncSession
from talk_to_pdf.backend.app.infrastructure.users.repositories import SqlAlchemyUserRepository


class UnitOfWork(Protocol):
    user_repo: SqlAlchemyUserRepository

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession):
        self._session = session
        self.user_repo = SqlAlchemyUserRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

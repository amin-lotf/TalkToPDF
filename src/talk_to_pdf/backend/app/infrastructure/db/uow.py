# app/infrastructure/db/uow.py
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.infrastructure.projects.repositories import SqlAlchemyProjectRepository
from talk_to_pdf.backend.app.infrastructure.users.repositories import SqlAlchemyUserRepository


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession):
        self._session = session
        self.user_repo = SqlAlchemyUserRepository(session)
        self.project_repo=SqlAlchemyProjectRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc:
            await self.rollback()
        else:
            await self.commit()

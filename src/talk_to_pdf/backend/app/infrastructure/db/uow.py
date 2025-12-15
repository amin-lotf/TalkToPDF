# app/infrastructure/db/uow.py
from typing import Protocol
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.domain.projects import ProjectRepository
from talk_to_pdf.backend.app.domain.users.repositories import UserRepository
from talk_to_pdf.backend.app.infrastructure.projects.repositories import SqlAlchemyProjectRepository
from talk_to_pdf.backend.app.infrastructure.users.repositories import SqlAlchemyUserRepository


class UnitOfWork(Protocol):
    user_repo: UserRepository
    project_repo: ProjectRepository
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


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

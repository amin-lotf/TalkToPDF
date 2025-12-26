from types import TracebackType
from typing import Protocol, Optional

from talk_to_pdf.backend.app.domain.indexing.repositories import DocumentIndexRepository, ChunkRepository
from talk_to_pdf.backend.app.domain.projects import ProjectRepository
from talk_to_pdf.backend.app.domain.users.repositories import UserRepository


class UnitOfWork(Protocol):
    user_repo: UserRepository
    project_repo: ProjectRepository
    index_repo : DocumentIndexRepository
    chunk_repo : ChunkRepository
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
            self,
            exc_type: Optional[type[BaseException]],
            exc: Optional[BaseException],
            tb: Optional[TracebackType],
    ) -> None: ...

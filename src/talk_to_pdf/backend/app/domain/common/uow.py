from typing import Protocol

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

from __future__ import annotations

from tests.unit.fakes.chunk_repo import FakeChunkRepository
from tests.unit.fakes.indexing_repos import  FakeDocumentIndexRepository
from tests.unit.fakes.project_repo import FakeProjectRepository
from tests.unit.fakes.user_repo import FakeUserRepository


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.user_repo = FakeUserRepository()

        # Keep placeholders if your UnitOfWork Protocol expects these attributes
        self.project_repo = FakeProjectRepository()
        self.index_repo = FakeDocumentIndexRepository()
        self.chunk_repo = FakeChunkRepository()

        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        # Mirror your real UoW behavior
        if exc is not None:
            await self.rollback()
        else:
            await self.commit()

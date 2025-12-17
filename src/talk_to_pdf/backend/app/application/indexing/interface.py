from __future__ import annotations

from typing import Protocol
from uuid import UUID


class IndexingRunner(Protocol):
    async def enqueue(self, *, index_id: UUID) -> None:
        """Schedule background indexing for this index_id."""
        ...

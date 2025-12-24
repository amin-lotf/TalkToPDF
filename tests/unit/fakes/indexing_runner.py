from __future__ import annotations

from uuid import UUID


class FakeIndexingRunner:
    def __init__(self, *, raise_on_enqueue: Exception | None = None) -> None:
        self.raise_on_enqueue = raise_on_enqueue
        self.enqueued: list[UUID] = []

    async def enqueue(self, *, index_id: UUID) -> None:
        if self.raise_on_enqueue:
            raise self.raise_on_enqueue
        self.enqueued.append(index_id)

    async def stop(self, *, index_id: UUID) -> None:
        return None

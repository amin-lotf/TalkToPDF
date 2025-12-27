from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncContextManager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession  # only for typing; not actually used


@dataclass
class FakeSession:
    commits: int = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeSessionContext(AsyncContextManager[FakeSession]):
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


# class FakeTextExtractor:
#     def __init__(self, *, text: str | None = "hello world", raise_exc: Exception | None = None) -> None:
#         self._text = text
#         self._exc = raise_exc
#         self.called_with: list[bytes] = []
#
#     def extract(self, *, content: bytes) -> str:
#         self.called_with.append(content)
#         if self._exc:
#             raise self._exc
#         return self._text or ""


class FakeEmbedder:
    def __init__(self, *, dims: int = 3) -> None:
        self.dims = dims
        self.calls: list[list[str]] = []

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        # deterministic vectors
        return [[float(i % self.dims) for i in range(self.dims)] for _ in texts]


class FakeEmbedderFactory:
    def __init__(self, embedder: FakeEmbedder) -> None:
        self._embedder = embedder
        self.created_with: list[Any] = []

    def create(self, cfg: Any) -> FakeEmbedder:
        self.created_with.append(cfg)
        return self._embedder

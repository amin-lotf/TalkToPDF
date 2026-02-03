from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncContextManager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession  # only for typing; not actually used
from talk_to_pdf.backend.app.domain.indexing.value_objects import Block, ChunkDraft


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


class FakePdfToXmlConverter:
    def __init__(self, *, xml: str = "<TEI></TEI>", raise_exc: Exception | None = None) -> None:
        self._xml = xml
        self._exc = raise_exc
        self.called_with: list[bytes] = []

    def convert(self, *, content: bytes) -> str:
        self.called_with.append(content)
        if self._exc:
            raise self._exc
        return self._xml


class FakeBlockExtractor:
    def __init__(self, *, blocks: list[Block] | None = None, raise_exc: Exception | None = None) -> None:
        self._blocks = blocks or [
            Block(
                text="hello world",
                meta={"div_index": 0, "kind": "paragraph", "head": None, "xml_id": None, "targets": []},
            )
        ]
        self._exc = raise_exc
        self.called_with: list[str] = []

    def extract(self, *, xml: str) -> list[Block]:
        self.called_with.append(xml)
        if self._exc:
            raise self._exc
        return list(self._blocks)


class FakeBlockChunker:
    def __init__(self, *, chunks: list[ChunkDraft] | None = None) -> None:
        self._chunks = chunks

    def chunk(self, *, blocks: list[Block]) -> list[ChunkDraft]:
        if self._chunks is not None:
            return list(self._chunks)
        text = "\n\n".join(b.text for b in blocks if b.text)
        return [
            ChunkDraft(
                chunk_index=0,
                blocks=list(blocks),
                text=text,
                meta={"block_count": len(blocks)},
            )
        ]


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

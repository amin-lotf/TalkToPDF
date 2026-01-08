from typing import Protocol

from talk_to_pdf.backend.app.domain.common.value_objects import Chunk


class Reranker(Protocol):
    async def rank(self,query: str, candidates: list[Chunk]) -> list[Chunk]:...
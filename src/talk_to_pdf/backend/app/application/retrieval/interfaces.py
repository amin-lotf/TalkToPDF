from typing import Protocol

from talk_to_pdf.backend.app.domain.common.value_objects import Chunk, ChatTurn


class Reranker(Protocol):
    async def rank(self,query: str, candidates: list[Chunk]) -> list[Chunk]:...


class QueryRewriter(Protocol):
    async def rewrite(self, *, query: str, history: list[ChatTurn]) -> str:...
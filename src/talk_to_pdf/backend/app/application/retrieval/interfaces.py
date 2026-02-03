from typing import Protocol

from talk_to_pdf.backend.app.application.retrieval.value_objects import MultiQueryRewriteResult, MergeResult
from talk_to_pdf.backend.app.domain.common.value_objects import Chunk, ChatTurn
from talk_to_pdf.backend.app.domain.retrieval.value_objects import ChunkMatch, RerankContext


class Reranker(Protocol):
    async def rank(
            self,
            query: str,
            candidates: list[Chunk],
            *,
            top_n: int | None = None,
            ctx: RerankContext | None = None,
    ) -> list[Chunk]: ...


class QueryRewriter(Protocol):
    async def rewrite(self, *, query: str, history: list[ChatTurn]) -> str:...

    async def rewrite_queries_with_metrics(
        self, *, query: str, history: list[ChatTurn]
    ) -> MultiQueryRewriteResult: ...

    async def rewrite_with_metrics(
        self, *, query: str, history: list[ChatTurn]
    ) -> MultiQueryRewriteResult: ...


class RetrievalResultMerger(Protocol):
    async def merge(
        self,
        *,
        query_texts: list[str],
        per_query_matches: list[list[ChunkMatch]],
        top_k: int,
        original_query: str,
    ) -> MergeResult: ...

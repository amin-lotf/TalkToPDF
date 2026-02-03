# talk_to_pdf/backend/app/application/retrieval/use_cases/build_index_context.py
from __future__ import annotations

import time
from typing import Any, Callable
from uuid import UUID

from talk_to_pdf.backend.app.application.common.dto import SearchInputDTO, ContextPackDTO, ContextChunkDTO
from talk_to_pdf.backend.app.application.common.progress import ProgressEvent, ProgressSink
from talk_to_pdf.backend.app.application.common.interfaces import EmbedderFactory
from talk_to_pdf.backend.app.application.retrieval.interfaces import Reranker, QueryRewriter, RetrievalResultMerger
from talk_to_pdf.backend.app.application.retrieval.mappers import create_context_pack_dto
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.common.value_objects import Vector, Chunk, EmbedConfig
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.common.enums import VectorMetric
from talk_to_pdf.backend.app.domain.retrieval.errors import InvalidQuery, IndexNotFoundOrForbidden, IndexNotReady, \
    InvalidRetrieval
from talk_to_pdf.backend.app.domain.retrieval.value_objects import ChunkMatch





class NullProgressSink:
    async def emit(self, event: ProgressEvent) -> None:
        return


# ----------------------------
# Helpers
# ----------------------------

def _clamp_int(name: str, v: int, *, lo: int, hi: int) -> int:
    if not isinstance(v, int):
        raise ValueError(f"{name} must be int")
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _is_blank(s: str) -> bool:
    return not s or not s.strip()





# ----------------------------
# The Use Case
# ----------------------------

class BuildIndexContextUseCase:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        *,
        embedder_factory: EmbedderFactory,
        reranker: Reranker | None = None,
        progress: ProgressSink | None = None,
        metric: VectorMetric = VectorMetric.COSINE,
        query_rewriter: QueryRewriter,
        retrieval_merger: RetrievalResultMerger,
        # guardrails to avoid abuse / accidental huge loads
        max_top_k: int,
        max_top_n: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._embedder_factory = embedder_factory
        self._reranker = reranker
        self._progress: ProgressSink = progress or NullProgressSink()
        self._metric = metric
        self._query_rewriter = query_rewriter
        self._retrieval_merger = retrieval_merger
        self._max_top_k = max_top_k
        self._max_top_n = max_top_n

    async def execute(self, dto: SearchInputDTO) -> ContextPackDTO:
        if _is_blank(dto.query):
            raise InvalidQuery("Query must not be blank")

        top_k = _clamp_int("top_k", dto.top_k, lo=1, hi=self._max_top_k)
        top_n = _clamp_int("top_n", dto.top_n, lo=1, hi=self._max_top_n)
        if top_n > top_k:
            # make it predictable: never ask reranker for more than you retrieved
            top_n = top_k

        # -----------------------------------
        # 1) Authz + ready index (single query)
        # -----------------------------------
        uow = self._uow_factory()
        async with uow:
            idx = await uow.index_repo.get_by_owner_project_and_id(
                owner_id=dto.owner_id,
                project_id=dto.project_id,
                index_id=dto.index_id,
            )
            if not idx:
                raise IndexNotFoundOrForbidden()

            if idx.status != IndexStatus.READY:
                raise IndexNotReady(index_id=str(dto.index_id))
            # Must be the SAME config used for chunk embeddings.
            embed_cfg: EmbedConfig = idx.embed_config
            embed_sig = embed_cfg.signature()

        # ----------------
        # 2) Rewrite query into multiple sub-queries and embed
        # ----------------
        rewrite_start = time.time()
        rewrite_result = await self._query_rewriter.rewrite_queries_with_metrics(
            query=dto.query, history=dto.message_history
        )
        rewrite_latency = time.time() - rewrite_start

        rewritten_queries = [q for q in rewrite_result.queries if not _is_blank(q)]
        if not rewritten_queries:
            rewritten_queries = [(dto.query or "").strip()]


        await self._progress.emit(
            ProgressEvent(
                name="multi_rewrite_done",
                payload={
                    "queries": rewritten_queries,
                    "prompt_tokens": rewrite_result.prompt_tokens,
                    "completion_tokens": rewrite_result.completion_tokens,
                    "latency": rewrite_latency,
                },
            )
        )

        embedder = self._embedder_factory.create(embed_cfg)
        await self._progress.emit(
            ProgressEvent(
                name="embed_queries_start",
                payload={"index_id": str(dto.index_id), "queries": len(rewritten_queries)},
            )
        )

        vectors = await embedder.aembed_documents(rewritten_queries)
        if not vectors or len(vectors) != len(rewritten_queries):
            raise InvalidRetrieval("Embedding provider returned empty vectors")

        query_vectors: list[Vector] = []
        for i, vec in enumerate(vectors):
            if not vec:
                raise InvalidRetrieval(f"Embedding provider returned empty vector for query #{i}")
            query_vectors.append(Vector.from_list(vec))

        await self._progress.emit(
            ProgressEvent(
                name="embed_queries_done",
                payload={"dim": query_vectors[0].dim if query_vectors else None, "count": len(query_vectors)},
            )
        )

        # ---------------------------------------------
        # 3) Vector similarity search (scoped properly)
        # ---------------------------------------------
        await self._progress.emit(
            ProgressEvent(
                name="vector_search_start",
                payload={
                    "index_id": str(dto.index_id),
                    "top_k": top_k,
                    "queries": len(query_vectors),
                    "embed_signature": embed_sig,
                    "metric": self._metric.value if hasattr(self._metric, "value") else str(self._metric),
                },
            )
        )

        per_query_matches: list[list[ChunkMatch]] = []
        async with uow:
            for idx, qvec in enumerate(query_vectors):
                matches = await uow.chunk_search_repo.similarity_search(
                    query=qvec,
                    top_k=top_k,
                    embed_signature=embed_sig,
                    index_id=dto.index_id,
                    metric=self._metric,
                )
                per_query_matches.append(matches)
                await self._progress.emit(
                    ProgressEvent(
                        name="vector_search_done",
                        payload={
                            "query_index": idx,
                            "top_k": top_k,
                            "returned": len(matches),
                        },
                    )
                )

        merge_result = await self._retrieval_merger.merge(
            query_texts=rewritten_queries,
            per_query_matches=per_query_matches,
            top_k=top_k,
            top_n=top_n,
            original_query=dto.query,
        )

        await self._progress.emit(
            ProgressEvent(
                name="merge_done",
                payload={
                    "total_candidates": merge_result.total_candidates,
                    "unique_candidates": merge_result.unique_candidates,
                    "selected": len(merge_result.matches),
                },
            )
        )

        if not merge_result.matches:
            return ContextPackDTO(
                index_id=dto.index_id,
                project_id=dto.project_id,
                query=dto.query,
                original_query=dto.query,
                embed_signature=embed_sig,
                metric=self._metric,
                chunks=[],
                rewritten_query=rewrite_result.rewritten_query,
                rewritten_queries=rewritten_queries,
                rewrite_strategy=rewrite_result.strategy,
                rewrite_prompt_tokens=rewrite_result.prompt_tokens,
                rewrite_completion_tokens=rewrite_result.completion_tokens,
                rewrite_latency=rewrite_latency,
            )

        # ---------------------------------------
        # 4) Load chunks by ids (scoped by index_id)
        # ---------------------------------------
        match_ids: list[UUID] = [m.chunk_id for m in merge_result.matches]
        score_by_id: dict[UUID, float] = merge_result.score_by_id

        await self._progress.emit(
            ProgressEvent(
                name="load_chunks_start",
                payload={"count": len(match_ids)},
            )
        )

        async with uow:
            chunks: list[Chunk] = await uow.chunk_repo.get_many_by_ids_for_index(
                index_id=dto.index_id,
                ids=match_ids,
            )

        # Keep the similarity ranking order (match_ids order), but only for chunks we actually loaded
        chunk_by_id = {c.id: c for c in chunks}
        ordered_chunks: list[Chunk] = [chunk_by_id[cid] for cid in match_ids if cid in chunk_by_id]

        await self._progress.emit(
            ProgressEvent(
                name="load_chunks_done",
                payload={"loaded": len(ordered_chunks)},
            )
        )

        # ----------------
        # 5) Optional rerank
        # ----------------
        final_chunks: list[Chunk] = ordered_chunks
        reranked = False

        if self._reranker and len(ordered_chunks) > 1:
            await self._progress.emit(
                ProgressEvent(
                    name="rerank_start",
                    payload={
                        "candidates": len(ordered_chunks),
                        "timeout_s": float(dto.rerank_timeout_s),
                    },
                )
            )

            final_chunks, reranked = await self._retrieval_merger.rerank(
                original_query=dto.query,
                candidates=ordered_chunks,
                reranker=self._reranker,
                timeout_s=float(dto.rerank_timeout_s),
            )

            await self._progress.emit(
                ProgressEvent(
                    name="rerank_done",
                    payload={"reranked": reranked, "candidates": len(ordered_chunks)},
                )
            )

        # --------------
        # 6) Build output
        # --------------
        return create_context_pack_dto(
            dto,
            final_chunks[:top_n],
            score_by_id,
            embed_sig,
            self._metric,
            merge_result.matched_by,
            rewritten_query=rewrite_result.rewritten_query,
            rewritten_queries=rewritten_queries,
            rewrite_strategy=rewrite_result.strategy,
            rewrite_prompt_tokens=rewrite_result.prompt_tokens,
            rewrite_completion_tokens=rewrite_result.completion_tokens,
            rewrite_latency=rewrite_latency,
        )

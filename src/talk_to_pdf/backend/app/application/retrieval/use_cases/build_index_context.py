# talk_to_pdf/backend/app/application/retrieval/use_cases/build_index_context.py
from __future__ import annotations

import time
from typing import Any, Callable
from uuid import UUID

import anyio

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
from talk_to_pdf.backend.app.domain.retrieval.value_objects import ChunkMatch, RerankContext


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
        else:
            rewritten_queries.append(dto.query or "")


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
            return create_context_pack_dto(
                dto,
                chunks=[],
                scores={},
                embed_signature=embed_sig,
                metric=self._metric,
                rewritten_results=rewrite_result,
                rewritten_queries=rewritten_queries,
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
        # 5) Optional rerank (fail-open + timeout)
        # ----------------
        final_chunks: list[Chunk] = ordered_chunks
        reranked = False
        rerank_latency = 0.0
        rerank_timed_out = False
        rerank_error: str | None = None

        # Safety clamps
        timeout_s = float(getattr(dto, "rerank_timeout_s", 0.0) or 0.0)
        if timeout_s < 0:
            timeout_s = 0.0

        # Never ask reranker for more than you will return / more than you have.
        rerank_top_n = min(top_n, len(ordered_chunks))

        if (
                self._reranker
                and len(ordered_chunks) > 1
                and rerank_top_n > 0
                and timeout_s > 0.0
        ):
            await self._progress.emit(
                ProgressEvent(
                    name="rerank_start",
                    payload={
                        "candidates": len(ordered_chunks),
                        "top_n": rerank_top_n,
                        "timeout_s": timeout_s,
                    },
                )
            )

            # Build context for reranker (optional)
            # If you don't have candidate signals, keep ctx minimal.
            ctx = RerankContext(
                original_query=dto.query,
                sub_queries=rewritten_queries,
                candidate_signals=getattr(merge_result, "candidate_signals", None),  # optional
            )

            t0 = time.time()
            try:
                # fail_after raises TimeoutError if exceeded
                with anyio.fail_after(timeout_s):
                    ranked_chunks = await self._reranker.rank(
                        query=dto.query,  # original intent anchor
                        candidates=ordered_chunks,
                        top_n=rerank_top_n,  # your new param
                        ctx=ctx,
                    )

                rerank_latency = time.time() - t0

                # Defensive: keep only chunks we know, preserve reranker order
                # (If reranker returns garbage/missing, your reranker already fail-opens,
                # but keep a final guard here.)
                if ranked_chunks:
                    # Ensure uniqueness + stable
                    seen: set[UUID] = set()
                    cleaned: list[Chunk] = []
                    for c in ranked_chunks:
                        if c.id not in seen:
                            cleaned.append(c)
                            seen.add(c.id)

                    # Ensure we didn’t lose anything critical (optional)
                    # Append missing in original order
                    missing = [c for c in ordered_chunks if c.id not in seen]
                    final_chunks = cleaned + missing
                    reranked = True
                else:
                    final_chunks = ordered_chunks

            except TimeoutError:
                rerank_latency = time.time() - t0
                rerank_timed_out = True
                final_chunks = ordered_chunks  # fail-open
            except Exception as e:
                rerank_latency = time.time() - t0
                rerank_error = f"{type(e).__name__}: {e}"
                final_chunks = ordered_chunks  # fail-open

            await self._progress.emit(
                ProgressEvent(
                    name="rerank_done",
                    payload={
                        "reranked": reranked,
                        "timed_out": rerank_timed_out,
                        "error": rerank_error,
                        "latency": rerank_latency,
                        "returned": min(len(final_chunks), rerank_top_n),
                    },
                )
            )
        else:
            # If reranker is disabled or timeout is 0, emit a lightweight event if you want observability.
            await self._progress.emit(
                ProgressEvent(
                    name="rerank_done",
                    payload={
                        "reranked": False,
                        "skipped": True,
                        "reason": (
                            "no_reranker"
                            if not self._reranker
                            else "not_enough_candidates"
                            if len(ordered_chunks) <= 1
                            else "timeout_disabled"
                        ),
                    },
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
            rewritten_results=rewrite_result,
            rewritten_queries=rewritten_queries,
            rewrite_latency=rewrite_latency,
        )

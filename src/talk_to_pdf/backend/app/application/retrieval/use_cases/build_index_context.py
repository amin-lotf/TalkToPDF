# talk_to_pdf/backend/app/application/retrieval/use_cases/build_index_context.py
from __future__ import annotations

import asyncio
import time
from typing import Any, Callable
from uuid import UUID

from talk_to_pdf.backend.app.application.common.dto import SearchInputDTO, ContextPackDTO, ContextChunkDTO
from talk_to_pdf.backend.app.application.common.progress import ProgressEvent, ProgressSink
from talk_to_pdf.backend.app.application.common.interfaces import EmbedderFactory
from talk_to_pdf.backend.app.application.retrieval.interfaces import Reranker, QueryRewriter
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
        query_rewriter:QueryRewriter,
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
        # 2) Rewrite query and embed
        # ----------------
        await self._progress.emit(
            ProgressEvent(
                name="embed_query_start",
                payload={"index_id": str(dto.index_id)},
            )
        )

        # Rewrite query with metrics and latency tracking
        rewrite_start = time.time()
        from talk_to_pdf.backend.app.infrastructure.reply.query_rewriter.openai_query_rewriter import QueryRewriteResult
        rewrite_result = await self._query_rewriter.rewrite_with_metrics(query=dto.query, history=dto.message_history)
        rewrite_latency = time.time() - rewrite_start

        rewritten_query = rewrite_result.rewritten_query
        rewrite_prompt_tokens = rewrite_result.prompt_tokens
        rewrite_completion_tokens = rewrite_result.completion_tokens

        embedder =  self._embedder_factory.create(embed_cfg)
        vectors = await embedder.aembed_documents([rewritten_query])
        if not vectors or not vectors[0]:
            raise InvalidRetrieval("Embedding provider returned empty vector")
        qvec = Vector.from_list(vectors[0])

        await self._progress.emit(
            ProgressEvent(
                name="embed_query_done",
                payload={"dim": qvec.dim},
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
                    "embed_signature": embed_sig,
                    "metric": self._metric.value if hasattr(self._metric, "value") else str(self._metric),
                },
            )
        )

        async with uow:
            matches: list[ChunkMatch] = await uow.chunk_search_repo.similarity_search(
                query=qvec,
                top_k=top_k,
                embed_signature=embed_sig,
                index_id=dto.index_id,
                metric=self._metric,
            )

        await self._progress.emit(
            ProgressEvent(
                name="vector_search_done",
                payload={"returned": len(matches)},
            )
        )

        if not matches:
            return ContextPackDTO(
                index_id=dto.index_id,
                project_id=dto.project_id,
                query=dto.query,
                embed_signature=embed_sig,
                metric=self._metric,
                chunks=[],
                rewritten_query=rewritten_query,
            )

        # ---------------------------------------
        # 4) Load chunks by ids (scoped by index_id)
        # ---------------------------------------
        match_ids: list[UUID] = [m.chunk_id for m in matches]  # type: ignore[attr-defined]
        score_by_id: dict[UUID, float] = {
            m.chunk_id: float(m.score)  # type: ignore[attr-defined]
            for m in matches
        }

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
            try:
                # Use case controls timeboxing (my recommendation)
                final_chunks = await asyncio.wait_for(
                    self._reranker.rank(dto.query, ordered_chunks),
                    timeout=max(0.0, float(dto.rerank_timeout_s)),
                )
                reranked = True
                # Safety: ensure returned chunks are subset of candidates
                allowed = {c.id for c in ordered_chunks}
                final_chunks = [c for c in final_chunks if c.id in allowed]
                if not final_chunks:
                    final_chunks = ordered_chunks
                    reranked = False
            except asyncio.TimeoutError:
                final_chunks = ordered_chunks
                reranked = False
            except Exception:
                # Don’t fail the request because rerank died; just fallback.
                final_chunks = ordered_chunks
                reranked = False

            await self._progress.emit(
                ProgressEvent(
                    name="rerank_done",
                    payload={"reranked": reranked},
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
            rewritten_query=rewritten_query,
            rewrite_prompt_tokens=rewrite_prompt_tokens,
            rewrite_completion_tokens=rewrite_completion_tokens,
            rewrite_latency=rewrite_latency,
        )

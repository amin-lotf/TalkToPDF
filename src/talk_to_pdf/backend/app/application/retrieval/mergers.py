from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID

from talk_to_pdf.backend.app.application.retrieval.interfaces import RetrievalResultMerger, Reranker
from talk_to_pdf.backend.app.application.retrieval.value_objects import MergeResult
from talk_to_pdf.backend.app.domain.common.value_objects import Chunk
from talk_to_pdf.backend.app.domain.retrieval.value_objects import ChunkMatch


@dataclass(frozen=True, slots=True)
class _AggregatedMatch:
    score: float
    chunk_index: int
    matched_by: set[int]


class DeterministicRetrievalResultMerger(RetrievalResultMerger):
    """
    Merge + dedupe retrieval outputs across multiple query rewrites.

    Strategy:
    - Deduplicate by chunk_id.
    - Aggregate score using max similarity across all queries.
    - Preserve which queries matched each chunk (matched_by).
    - Return top_k candidates sorted by aggregated score (higher is better).
    """

    async def merge(
        self,
        *,
        query_texts: list[str],
        per_query_matches: list[list[ChunkMatch]],
        top_k: int,
        top_n: int,  # kept to satisfy interface; top_k guards the candidate pool
        original_query: str,
    ) -> MergeResult:
        _ = (query_texts, original_query)
        aggregated: dict[UUID, _AggregatedMatch] = {}
        total_candidates = 0

        for q_idx, matches in enumerate(per_query_matches):
            total_candidates += len(matches)
            for match in matches:
                key = match.chunk_id
                existing = aggregated.get(key)
                if existing is None:
                    aggregated[key] = _AggregatedMatch(
                        score=float(match.score),
                        chunk_index=match.chunk_index,
                        matched_by={q_idx},
                    )
                    continue

                existing.matched_by.add(q_idx)
                if match.score > existing.score:
                    aggregated[key] = _AggregatedMatch(
                        score=float(match.score),
                        chunk_index=match.chunk_index,
                        matched_by=existing.matched_by,
                    )

        merged_matches: list[ChunkMatch] = []
        for key, agg in aggregated.items():
            merged_matches.append(
                ChunkMatch(
                    chunk_id=key,
                    chunk_index=agg.chunk_index,
                    score=agg.score,
                    matched_by=sorted(agg.matched_by),
                )
            )

        merged_matches.sort(key=lambda m: m.score, reverse=True)
        selected = merged_matches[: max(top_k, top_n)]

        score_by_id = {m.chunk_id: float(m.score) for m in selected}
        matched_by = {m.chunk_id: list(m.matched_by or []) for m in selected}

        return MergeResult(
            matches=selected,
            score_by_id=score_by_id,
            matched_by=matched_by,
            total_candidates=total_candidates,
            unique_candidates=len(aggregated),
        )

    async def rerank(
        self,
        *,
        original_query: str,
        candidates: list[Chunk],
        reranker: Reranker | None,
        timeout_s: float,
    ) -> tuple[list[Chunk], bool]:
        """
        Apply optional reranker with timeout and safe fallback.
        """
        if not reranker or len(candidates) <= 1:
            return candidates, False

        try:
            reranked = await asyncio.wait_for(
                reranker.rank(original_query, candidates),
                timeout=max(0.0, float(timeout_s)),
            )
            allowed = {c.id for c in candidates}
            reranked = [c for c in reranked if c.id in allowed]
            if not reranked:
                return candidates, False
            return reranked, True
        except asyncio.TimeoutError:
            return candidates, False
        except Exception:
            return candidates, False

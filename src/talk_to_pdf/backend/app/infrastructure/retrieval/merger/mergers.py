from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID

from talk_to_pdf.backend.app.application.retrieval.interfaces import RetrievalResultMerger, Reranker
from talk_to_pdf.backend.app.application.retrieval.value_objects import MergeResult
from talk_to_pdf.backend.app.domain.common.enums import MatchSource
from talk_to_pdf.backend.app.domain.common.value_objects import Chunk
from talk_to_pdf.backend.app.domain.retrieval.value_objects import ChunkMatch


@dataclass(frozen=True, slots=True)
class _AggregatedMatch:
    score: float
    chunk_index: int
    source:MatchSource
    matched_by: set[int]


class DeterministicRetrievalResultMerger:
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
                        source=match.source
                    )
                    continue

                existing.matched_by.add(q_idx)
                if match.score > existing.score:
                    aggregated[key] = _AggregatedMatch(
                        score=float(match.score),
                        chunk_index=match.chunk_index,
                        matched_by=existing.matched_by,
                        source=match.source
                    )

        merged_matches: list[ChunkMatch] = []
        for key, agg in aggregated.items():
            merged_matches.append(
                ChunkMatch(
                    chunk_id=key,
                    chunk_index=agg.chunk_index,
                    score=agg.score,
                    source=agg.source,
                    matched_by=sorted(agg.matched_by),
                )
            )

        merged_matches.sort(key=lambda m: m.score, reverse=True)
        selected = merged_matches[: top_k]

        score_by_id = {m.chunk_id: float(m.score) for m in selected}
        matched_by = {m.chunk_id: list(m.matched_by or []) for m in selected}

        return MergeResult(
            matches=selected,
            score_by_id=score_by_id,
            matched_by=matched_by,
            total_candidates=total_candidates,
            unique_candidates=len(aggregated),
        )

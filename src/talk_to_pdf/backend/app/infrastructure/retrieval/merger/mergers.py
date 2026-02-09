from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from talk_to_pdf.backend.app.application.retrieval.value_objects import MergeResult
from talk_to_pdf.backend.app.domain.common.enums import MatchSource
from talk_to_pdf.backend.app.domain.retrieval.value_objects import ChunkMatch



class DeterministicRetrievalResultMerger:
    """
    Merge + dedupe retrieval outputs across multiple query rewrites.

    Strategy:
    - For each query rewrite, combine vector + fts hits per chunk_id into one score
      using weighted normalized scores.
    - Deduplicate across queries by chunk_id.
    - Aggregate score using max combined score across queries.
    - Preserve which query indices matched each chunk (matched_by).
    - Return top_k by aggregated score (higher is better).
    """
    def __init__(self,w_vec:float=0.65,w_fts:float=0.35) -> None:
        self.w_vec: float = w_vec
        self.w_fts: float = w_fts

    async def merge(
        self,
        *,
        query_texts: list[str],
        per_query_vec_matches: list[list[ChunkMatch]],
        per_query_fts_matches: list[list[ChunkMatch]],
        top_k: int,
        original_query: str,
    ) -> MergeResult:
        _ = (query_texts, original_query)

        if top_k <= 0:
            return MergeResult(
                matches=[],
                score_by_id={},
                matched_by={},
                total_candidates=0,
                unique_candidates=0,
            )

        n_q = len(query_texts)

        # Align lists to number of queries (defensive)
        vec_lists = (per_query_vec_matches or [])[:n_q]
        fts_lists = (per_query_fts_matches or [])[:n_q]
        if len(vec_lists) < n_q:
            vec_lists = vec_lists + [[] for _ in range(n_q - len(vec_lists))]
        if len(fts_lists) < n_q:
            fts_lists = fts_lists + [[] for _ in range(n_q - len(fts_lists))]

        def _minmax_norm(scores: dict[UUID, float]) -> dict[UUID, float]:
            if not scores:
                return {}
            vals = list(scores.values())
            lo, hi = min(vals), max(vals)
            if hi - lo < 1e-12:
                return {k: 1.0 for k in scores}
            return {k: (v - lo) / (hi - lo) for k, v in scores.items()}

        aggregated: dict[UUID, ChunkMatch] = {}
        total_candidates = 0

        for q_idx in range(n_q):
            vec_matches = vec_lists[q_idx]
            fts_matches = fts_lists[q_idx]
            total_candidates += len(vec_matches) + len(fts_matches)

            # raw dicts per source
            vec_raw: dict[UUID, float] = {}
            vec_idx: dict[UUID, int] = {}
            for m in vec_matches:
                vec_raw[m.chunk_id] = float(m.score)
                vec_idx[m.chunk_id] = m.chunk_index

            fts_raw: dict[UUID, float] = {}
            fts_idx: dict[UUID, int] = {}
            for m in fts_matches:
                fts_raw[m.chunk_id] = float(m.score)
                fts_idx[m.chunk_id] = m.chunk_index

            # normalize within this query per source
            vec_norm = _minmax_norm(vec_raw)
            fts_norm = _minmax_norm(fts_raw)

            ids = set(vec_raw) | set(fts_raw)
            if not ids:
                continue

            for cid in ids:
                v = vec_norm.get(cid, 0.0)
                f = fts_norm.get(cid, 0.0)
                combined = (self.w_vec * v) + (self.w_fts * f)

                # chunk index: prefer vector index; else fts index; else -1
                cindex = vec_idx.get(cid, fts_idx.get(cid, -1))

                # source: keep enum unchanged; choose one deterministically
                if cid in vec_raw:
                    src = MatchSource.VECTOR
                else:
                    src = MatchSource.FTS

                existing = aggregated.get(cid)
                if existing is None:
                    aggregated[cid] = ChunkMatch(
                        chunk_id=cid,
                        chunk_index=cindex,
                        score=float(combined),
                        source=src,
                        matched_by={q_idx},
                    )
                    continue

                prev_matched = existing.matched_by or set()
                new_matched = set(prev_matched)
                new_matched.add(q_idx)

                # max score across queries
                if combined > float(existing.score):
                    aggregated[cid] = ChunkMatch(
                        chunk_id=cid,
                        chunk_index=cindex if cindex != -1 else existing.chunk_index,
                        score=float(combined),
                        source=src,
                        matched_by=new_matched,
                    )
                else:
                    # keep score/source/chunk_index, just update matched_by
                    aggregated[cid] = ChunkMatch(
                        chunk_id=cid,
                        chunk_index=existing.chunk_index,
                        score=float(existing.score),
                        source=existing.source,
                        matched_by=new_matched,
                    )

        merged_matches = list(aggregated.values())
        merged_matches.sort(key=lambda m: (-float(m.score), m.chunk_index))
        selected = merged_matches[:top_k]

        score_by_id = {m.chunk_id: float(m.score) for m in selected}
        matched_by = {m.chunk_id: list(sorted(m.matched_by or [])) for m in selected}

        return MergeResult(
            matches=selected,
            score_by_id=score_by_id,
            matched_by=matched_by,
            total_candidates=total_candidates,
            unique_candidates=len(aggregated),
        )

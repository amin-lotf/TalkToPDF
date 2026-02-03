from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from talk_to_pdf.backend.app.domain.retrieval.value_objects import ChunkMatch


@dataclass(frozen=True, slots=True)
class MultiQueryRewriteResult:
    """
    Result of a multi-query rewrite step with token usage metrics.
    """

    queries: list[str]
    prompt_tokens: int
    completion_tokens: int
    strategy: str | None = None

    @property
    def rewritten_query(self) -> str:
        """
        Backwards-compatible primary query accessor.
        """
        return self.queries[0] if self.queries else ""


@dataclass(frozen=True, slots=True)
class MergeResult:
    """
    Aggregated retrieval output after merging per-query matches.
    """

    matches: list[ChunkMatch]
    score_by_id: dict[UUID, float]
    matched_by: dict[UUID, list[int]]
    total_candidates: int
    unique_candidates: int

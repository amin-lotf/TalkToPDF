from dataclasses import dataclass
from typing import Any
from uuid import UUID

from talk_to_pdf.backend.app.domain.common.enums import MatchSource


@dataclass(frozen=True, slots=True)
class RerankContext:
    """
    Optional context to help the reranker without changing the core intent:
    - original_query should remain the main query used for reranking.
    - sub_queries are supporting signals only.
    """
    original_query: str
    sub_queries: list[str] | None = None

    # Optional provenance/diagnostics that your merger can attach per candidate
    # Example shape:
    #   {"<chunk_uuid>": {"matched_by": [0,2], "agg_score": 0.41}}
    candidate_signals: dict[str, dict[str, Any]] | None = None



@dataclass(frozen=True, slots=True)
class ChunkMatch:
    """
    Retrieval result: which chunk matched and with what score/distance.
    """
    chunk_id: UUID
    chunk_index: int
    score: float  # interpretation depends on metric (similarity or negative distance)
    source: MatchSource
    matched_by: list[int] | None = None  # indexes of queries that retrieved this chunk





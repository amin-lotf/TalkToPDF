from typing import Any
from uuid import UUID

from talk_to_pdf.backend.app.application.common.dto import ContextChunkDTO, SearchInputDTO, ContextPackDTO
from talk_to_pdf.backend.app.domain.common.enums import VectorMetric
from talk_to_pdf.backend.app.domain.common.value_objects import Chunk

def _as_citation(chunk: Chunk) -> dict[str, Any] | None:
    """
    Opinionated default: treat chunk.meta as the citation payload if present.
    You can formalize later (page, bbox, offsets...).
    """
    if not chunk.meta:
        return None
    # If you already store page / source info in meta, this is good enough.
    return dict(chunk.meta)

def create_context_chunk_dto(
        chunks: list[Chunk],
        scores: dict[UUID, float],
        matched_by: dict[UUID, list[int]] | None = None
) -> list[ContextChunkDTO]:
    out_chunks: list[ContextChunkDTO] = []
    for c in chunks:
        out_chunks.append(
            ContextChunkDTO(
                chunk_id=c.id,
                chunk_index=c.chunk_index,
                text=c.text,
                score=scores.get(c.id, 0.0),  # keep similarity score even if reranked
                meta=c.meta,
                citation=_as_citation(c),
                matched_by=matched_by.get(c.id) if matched_by else None,
            )
        )
    return out_chunks


def create_context_pack_dto(
        search_input_dto:SearchInputDTO,
        chunks:list[Chunk],
        scores:dict[UUID,float],
        embed_signature:str,
        metric:VectorMetric,
        matched_by: dict[UUID, list[int]] | None = None,
        rewritten_query:str | None = None,
        rewritten_queries: list[str] | None = None,
        rewrite_strategy: str | None = None,
        rewrite_prompt_tokens:int = 0,
        rewrite_completion_tokens:int = 0,
        rewrite_latency:float | None = None,
)->ContextPackDTO:
    context_chunks = create_context_chunk_dto(chunks, scores, matched_by=matched_by)
    return ContextPackDTO(
        index_id=search_input_dto.index_id,
        project_id=search_input_dto.project_id,
        query=search_input_dto.query,
        original_query=search_input_dto.query,
        embed_signature=embed_signature,
        metric=metric,
        chunks=context_chunks,
        rewritten_query=rewritten_query,
        rewritten_queries=rewritten_queries,
        rewrite_strategy=rewrite_strategy,
        rewrite_prompt_tokens=rewrite_prompt_tokens,
        rewrite_completion_tokens=rewrite_completion_tokens,
        rewrite_latency=rewrite_latency,
    )

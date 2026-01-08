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

def create_context_chunk_dto(chunks:list[Chunk],scores:dict[UUID,float])->list[ContextChunkDTO]:
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
            )
        )
    return out_chunks


def create_context_pack_dto(
        search_input_dto:SearchInputDTO,
        chunks:list[Chunk],
        scores:dict[UUID,float],
        embed_signature:str,
        metric:VectorMetric
)->ContextPackDTO:
    context_chunks=create_context_chunk_dto(chunks,scores)
    return ContextPackDTO(
        index_id=search_input_dto.index_id,
        project_id=search_input_dto.project_id,
        query=search_input_dto.query,
        embed_signature=embed_signature,
        metric=metric,
        chunks=context_chunks,
    )
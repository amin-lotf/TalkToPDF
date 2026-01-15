from __future__ import annotations

from talk_to_pdf.backend.app.api.v1.reply.schemas import QueryRequest, ReplyResponse, ContextPackResponse, ContextChunkResponse
from talk_to_pdf.backend.app.application.reply.dto import ReplyOutputDTO, ReplyInputDTO


def to_search_project_context_input(dto: QueryRequest, *, owner_id) -> ReplyInputDTO:
    return ReplyInputDTO(
        project_id=dto.project_id,
        owner_id=owner_id,
        query=dto.query,
        top_k=dto.top_k,
        top_n=dto.top_n,
        rerank_timeout_s=float(dto.rerank_timeout_s),
    )


def to_reply_response(out: ReplyOutputDTO) -> ReplyResponse:
    return ReplyResponse(
        query=out.query,
        answer=out.answer,
        context=ContextPackResponse(
            index_id=out.context.index_id,
            project_id=out.context.project_id,
            query=out.context.query,
            embed_signature=out.context.embed_signature,
            metric=str(out.context.metric.value if hasattr(out.context.metric, "value") else out.context.metric),
            chunks=[
                ContextChunkResponse(
                    chunk_id=c.chunk_id,
                    chunk_index=c.chunk_index,
                    text=c.text,
                    score=float(c.score),
                    meta=c.meta,
                    citation=c.citation,
                )
                for c in out.context.chunks
            ],
        ),
    )

from uuid import UUID

from talk_to_pdf.backend.app.application.common.dto import SearchInputDTO
from talk_to_pdf.backend.app.application.reply.dto import ReplyInputDTO


def build_search_input_dto(dto: ReplyInputDTO, index_id:UUID) -> SearchInputDTO:
    return SearchInputDTO(
        project_id=dto.project_id,
        owner_id=dto.owner_id,
        index_id=index_id,
        query=dto.query,
        top_k=dto.top_k,
        top_n=dto.top_n,
        rerank_timeout_s=dto.rerank_timeout_s,
    )
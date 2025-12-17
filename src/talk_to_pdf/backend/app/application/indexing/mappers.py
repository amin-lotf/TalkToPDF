from typing import Optional, Mapping, Any
from talk_to_pdf.backend.app.application.indexing.dto import  IndexStatusDTO
from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex





def to_index_status_dto(
    index: DocumentIndex,
    meta: Optional[Mapping[str, Any]] = None,
) -> IndexStatusDTO:
    return IndexStatusDTO(
        project_id=index.project_id,
        document_id=index.document_id,
        index_id=index.id,
        status=index.status,
        progress=index.progress,
        message=index.message,
        error=index.error,
        cancel_requested=index.cancel_requested,
        updated_at=index.updated_at,
        meta=meta,
    )
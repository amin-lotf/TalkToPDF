from uuid import UUID

from talk_to_pdf.backend.app.application.indexing.dto import (
    StartIndexingInputDTO,
    GetLatestIndexStatusInputDTO,
    GetIndexStatusByIdInputDTO,
    CancelIndexingInputDTO,
)


def get_start_indexing_input_dto(
    owner_id: UUID,
    project_id: UUID,
    document_id: UUID,
) -> StartIndexingInputDTO:
    return StartIndexingInputDTO(
        owner_id=owner_id,
        project_id=project_id,
        document_id=document_id,
    )


def get_get_latest_index_status_input_dto(
    owner_id: UUID,
    project_id: UUID,
) -> GetLatestIndexStatusInputDTO:
    return GetLatestIndexStatusInputDTO(
        owner_id=owner_id,
        project_id=project_id,
    )


def get_get_index_status_by_id_input_dto(
    owner_id: UUID,
    index_id: UUID,
) -> GetIndexStatusByIdInputDTO:
    return GetIndexStatusByIdInputDTO(
        owner_id=owner_id,
        index_id=index_id,
    )


def get_cancel_indexing_input_dto(
    owner_id: UUID,
    index_id: UUID,
) -> CancelIndexingInputDTO:
    return CancelIndexingInputDTO(
        owner_id=owner_id,
        index_id=index_id,
    )

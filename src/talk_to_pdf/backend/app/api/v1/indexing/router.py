from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from talk_to_pdf.backend.app.api.v1.users.deps import get_logged_in_user
from talk_to_pdf.backend.app.application.users import CurrentUserDTO

from talk_to_pdf.backend.app.api.v1.indexing.deps import (
    get_start_indexing_use_case,
    get_latest_index_status_use_case,
    get_index_status_use_case,
    get_cancel_indexing_use_case,
)
from talk_to_pdf.backend.app.api.v1.indexing.mappers import (
    get_start_indexing_input_dto,
    get_get_latest_index_status_input_dto,
    get_get_index_status_by_id_input_dto,
    get_cancel_indexing_input_dto,
)
from talk_to_pdf.backend.app.api.v1.indexing.schemas import IndexStatusResponse

from talk_to_pdf.backend.app.application.indexing.use_cases.start_indexing import StartIndexingUseCase
from talk_to_pdf.backend.app.application.indexing.use_cases.get_latest_index_status import GetLatestIndexStatusUseCase
from talk_to_pdf.backend.app.application.indexing.use_cases.get_index_status import GetIndexStatusUseCase
from talk_to_pdf.backend.app.application.indexing.use_cases.cancel_indexing import CancelIndexingUseCase

router = APIRouter(prefix="/indexing", tags=["indexing"])

logged_in_user_dep = Annotated[CurrentUserDTO, Depends(get_logged_in_user)]
start_indexing_dep = Annotated[StartIndexingUseCase, Depends(get_start_indexing_use_case)]
latest_index_status_dep = Annotated[GetLatestIndexStatusUseCase, Depends(get_latest_index_status_use_case)]
index_status_dep = Annotated[GetIndexStatusUseCase, Depends(get_index_status_use_case)]
cancel_indexing_dep = Annotated[CancelIndexingUseCase, Depends(get_cancel_indexing_use_case)]


@router.post(
    "/projects/{project_id}/documents/{document_id}/start",
    response_model=IndexStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_indexing(
    user: logged_in_user_dep,
    use_case: start_indexing_dep,
    project_id: UUID,
    document_id: UUID,
) -> IndexStatusResponse:
    dto = get_start_indexing_input_dto(
        owner_id=user.id,
        project_id=project_id,
        document_id=document_id,
    )
    index_dto = await use_case.execute(dto)
    return IndexStatusResponse.model_validate(index_dto)


@router.get(
    "/projects/{project_id}/latest",
    response_model=IndexStatusResponse,
)
async def get_latest_index_status(
    user: logged_in_user_dep,
    use_case: latest_index_status_dep,
    project_id: UUID,
) -> IndexStatusResponse:
    dto = get_get_latest_index_status_input_dto(owner_id=user.id, project_id=project_id)
    index_dto = await use_case.execute(dto)
    return IndexStatusResponse.model_validate(index_dto)


@router.get(
    "/{index_id}",
    response_model=IndexStatusResponse,
)
async def get_index_status(
    user: logged_in_user_dep,
    use_case: index_status_dep,
    index_id: UUID,
) -> IndexStatusResponse:
    dto = get_get_index_status_by_id_input_dto(owner_id=user.id, index_id=index_id)
    index_dto = await use_case.execute(dto)
    return IndexStatusResponse.model_validate(index_dto)


@router.post(
    "/{index_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_indexing(
    user: logged_in_user_dep,
    use_case: cancel_indexing_dep,
    index_id: UUID,
) -> None:
    dto = get_cancel_indexing_input_dto(owner_id=user.id, index_id=index_id)
    await use_case.execute(dto)
    return None

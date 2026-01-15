from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends,  status

from talk_to_pdf.backend.app.api.v1.reply.deps import get_stream_reply_use_case
from talk_to_pdf.backend.app.api.v1.reply.mappers import to_search_project_context_input, to_reply_response
from talk_to_pdf.backend.app.api.v1.reply.schemas import QueryRequest, ReplyResponse
from talk_to_pdf.backend.app.api.v1.users.deps import get_logged_in_user
from talk_to_pdf.backend.app.application.reply.use_cases.stream_reply import StreamReplyUseCase
from talk_to_pdf.backend.app.application.users import CurrentUserDTO


router = APIRouter(prefix="/query", tags=["query"])

logged_in_user_dep = Annotated[CurrentUserDTO, Depends(get_logged_in_user)]
stream_reply_dep = Annotated[StreamReplyUseCase, Depends(get_stream_reply_use_case)]


@router.post(
    "",
    response_model=ReplyResponse,
    status_code=status.HTTP_200_OK,
)
async def query_project(
    body: QueryRequest,
    user: logged_in_user_dep,
    uc: stream_reply_dep,
) -> ReplyResponse:
    app_dto = to_search_project_context_input(body, owner_id=user.id)
    out = await uc.execute(app_dto)
    return to_reply_response(out)


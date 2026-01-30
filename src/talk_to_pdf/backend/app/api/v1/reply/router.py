from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status, Query

from talk_to_pdf.backend.app.api.v1.reply.deps import (
    get_stream_reply_use_case,
    get_create_chat_use_case,
    get_get_chat_use_case,
    get_list_chats_use_case,
    get_delete_chat_use_case,
    get_get_chat_messages_use_case,
)
from talk_to_pdf.backend.app.api.v1.reply.mappers import (
    to_search_project_context_input,
    to_reply_response,
    to_create_chat_input_dto,
    to_list_chats_input_dto,
    to_get_chat_input_dto,
    to_delete_chat_input_dto,
    chat_dto_to_response,
    list_chats_dto_to_response,
    to_get_chat_messages_input_dto,
    list_messages_dto_to_response,
)
from talk_to_pdf.backend.app.api.v1.reply.schemas import (
    QueryRequest,
    ReplyResponse,
    CreateChatRequest,
    ChatResponse,
    ListChatsResponse,
    ListMessagesResponse,
)
from talk_to_pdf.backend.app.api.v1.users.deps import get_logged_in_user
from talk_to_pdf.backend.app.application.reply.use_cases.stream_reply import StreamReplyUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.create_chat import CreateChatUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.get_chat import GetChatUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.list_chats import ListChatsUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.delete_chat import DeleteChatUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.get_chat_messages import GetChatMessagesUseCase
from talk_to_pdf.backend.app.application.users import CurrentUserDTO


router = APIRouter(tags=["reply"])

logged_in_user_dep = Annotated[CurrentUserDTO, Depends(get_logged_in_user)]
stream_reply_dep = Annotated[StreamReplyUseCase, Depends(get_stream_reply_use_case)]
create_chat_dep = Annotated[CreateChatUseCase, Depends(get_create_chat_use_case)]
get_chat_dep = Annotated[GetChatUseCase, Depends(get_get_chat_use_case)]
list_chats_dep = Annotated[ListChatsUseCase, Depends(get_list_chats_use_case)]
delete_chat_dep = Annotated[DeleteChatUseCase, Depends(get_delete_chat_use_case)]
get_chat_messages_dep = Annotated[GetChatMessagesUseCase, Depends(get_get_chat_messages_use_case)]


# -------------------------
# Query endpoint
# -------------------------
@router.post(
    "/query",
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


# -------------------------
# Chat endpoints
# -------------------------
@router.post(
    "/chats",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat(
    body: CreateChatRequest,
    user: logged_in_user_dep,
    uc: create_chat_dep,
) -> ChatResponse:
    dto = to_create_chat_input_dto(body, owner_id=user.id)
    chat_dto = await uc.execute(dto)
    return chat_dto_to_response(chat_dto)


@router.get(
    "/projects/{project_id}/chats",
    response_model=ListChatsResponse,
    status_code=status.HTTP_200_OK,
)
async def list_chats(
    project_id: UUID,
    user: logged_in_user_dep,
    uc: list_chats_dep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListChatsResponse:
    dto = to_list_chats_input_dto(project_id, owner_id=user.id, limit=limit, offset=offset)
    chats = await uc.execute(dto)
    return list_chats_dto_to_response(chats)


@router.get(
    "/chats/{chat_id}",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def get_chat(
    chat_id: UUID,
    user: logged_in_user_dep,
    uc: get_chat_dep,
) -> ChatResponse:
    dto = to_get_chat_input_dto(chat_id, owner_id=user.id)
    chat_dto = await uc.execute(dto)
    return chat_dto_to_response(chat_dto)


@router.delete(
    "/chats/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_chat(
    chat_id: UUID,
    user: logged_in_user_dep,
    uc: delete_chat_dep,
) -> None:
    dto = to_delete_chat_input_dto(chat_id, owner_id=user.id)
    await uc.execute(dto)
    return None


# -------------------------
# Message endpoints
# -------------------------
@router.get(
    "/chats/{chat_id}/messages",
    response_model=ListMessagesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_chat_messages(
    chat_id: UUID,
    user: logged_in_user_dep,
    uc: get_chat_messages_dep,
    limit: int = Query(default=50, ge=1, le=100),
) -> ListMessagesResponse:
    dto = to_get_chat_messages_input_dto(chat_id, owner_id=user.id, limit=limit)
    messages = await uc.execute(dto)
    return list_messages_dto_to_response(messages)


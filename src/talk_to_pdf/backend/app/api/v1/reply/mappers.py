from __future__ import annotations

from uuid import UUID

from talk_to_pdf.backend.app.api.v1.reply.schemas import (
    QueryRequest,
    ReplyResponse,
    ContextPackResponse,
    ContextChunkResponse,
    CreateChatRequest,
    ChatResponse,
    ListChatsResponse,
    MessageResponse,
    ListMessagesResponse,
)
from talk_to_pdf.backend.app.application.reply.dto import (
    ReplyOutputDTO,
    ReplyInputDTO,
    CreateChatInputDTO,
    ChatDTO,
    ListChatsInputDTO,
    GetChatInputDTO,
    DeleteChatInputDTO,
    MessageDTO,
    GetChatMessagesInputDTO,
)


def to_search_project_context_input(dto: QueryRequest, *, owner_id) -> ReplyInputDTO:
    return ReplyInputDTO(
        chat_id=dto.chat_id,
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


# -------------------------
# Chat mappers
# -------------------------
def to_create_chat_input_dto(req: CreateChatRequest, *, owner_id: UUID) -> CreateChatInputDTO:
    return CreateChatInputDTO(
        owner_id=owner_id,
        project_id=req.project_id,
        title=req.title,
    )


def to_list_chats_input_dto(project_id: UUID, *, owner_id: UUID, limit: int = 50, offset: int = 0) -> ListChatsInputDTO:
    return ListChatsInputDTO(
        owner_id=owner_id,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )


def to_get_chat_input_dto(chat_id: UUID, *, owner_id: UUID) -> GetChatInputDTO:
    return GetChatInputDTO(
        owner_id=owner_id,
        chat_id=chat_id,
    )


def to_delete_chat_input_dto(chat_id: UUID, *, owner_id: UUID) -> DeleteChatInputDTO:
    return DeleteChatInputDTO(
        owner_id=owner_id,
        chat_id=chat_id,
    )


def chat_dto_to_response(dto: ChatDTO) -> ChatResponse:
    return ChatResponse(
        id=dto.id,
        owner_id=dto.owner_id,
        project_id=dto.project_id,
        title=dto.title,
        created_at=dto.created_at.isoformat(),
        updated_at=dto.updated_at.isoformat(),
    )


def list_chats_dto_to_response(dtos: list[ChatDTO]) -> ListChatsResponse:
    return ListChatsResponse(
        items=[chat_dto_to_response(dto) for dto in dtos]
    )


# -------------------------
# Message mappers
# -------------------------
def to_get_chat_messages_input_dto(chat_id: UUID, *, owner_id: UUID, limit: int = 50) -> GetChatMessagesInputDTO:
    return GetChatMessagesInputDTO(
        owner_id=owner_id,
        chat_id=chat_id,
        limit=limit,
    )


def message_dto_to_response(dto: MessageDTO) -> MessageResponse:
    return MessageResponse(
        id=dto.id,
        chat_id=dto.chat_id,
        role=dto.role.value if hasattr(dto.role, 'value') else str(dto.role),
        content=dto.content,
        created_at=dto.created_at.isoformat(),
        citations=dto.citations,
    )


def list_messages_dto_to_response(dtos: list[MessageDTO]) -> ListMessagesResponse:
    return ListMessagesResponse(
        items=[message_dto_to_response(dto) for dto in dtos]
    )

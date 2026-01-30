from __future__ import annotations

from uuid import UUID

from talk_to_pdf.backend.app.application.common.dto import SearchInputDTO, ContextPackDTO
from talk_to_pdf.backend.app.application.reply.dto import ChatDTO, ReplyInputDTO, MessageDTO, CreateChatInputDTO, \
    CreateMessageInputDTO, ReplyOutputDTO
from talk_to_pdf.backend.app.domain.reply import ChatRole
from talk_to_pdf.backend.app.domain.reply.entities import Chat, ChatMessage  # since you put both in entities.py


def build_search_input_dto(*, dto: ReplyInputDTO, index_id: UUID) -> SearchInputDTO:
    return SearchInputDTO(
        project_id=dto.project_id,
        owner_id=dto.owner_id,
        index_id=index_id,
        query=dto.query,
        top_k=dto.top_k,
        top_n=dto.top_n,
        rerank_timeout_s=dto.rerank_timeout_s,
    )


def chat_domain_to_dto(chat: Chat) -> ChatDTO:
    return ChatDTO(
        id=chat.id,
        owner_id=chat.owner_id,
        project_id=chat.project_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )

def create_chat_domain(chat_input_dto: CreateChatInputDTO) -> Chat:
    return Chat(
        owner_id=chat_input_dto.owner_id,
        project_id=chat_input_dto.project_id,
        title=chat_input_dto.title,
    )

def create_chat_message_domain(create_dto: CreateMessageInputDTO) -> ChatMessage:
    return ChatMessage(
        chat_id=create_dto.chat_id,
        role=create_dto.role,
        content=create_dto.content,
    )

def message_to_dto(msg: ChatMessage) -> MessageDTO:
    return MessageDTO(
        id=msg.id,
        chat_id=msg.chat_id,
        role=msg.role,
        content=msg.content,
        created_at=msg.created_at,
    )


def create_create_chat_message_input_dto(reply_input_dto:ReplyInputDTO,role:ChatRole,content:str)->CreateMessageInputDTO:
    return CreateMessageInputDTO(
        owner_id=reply_input_dto.owner_id,
        chat_id=reply_input_dto.chat_id,
        role=role,
        content=content,
    )

def create_reply_output_dto(dto: ReplyInputDTO, answer_text: str, context: ContextPackDTO) -> ReplyOutputDTO:
    return ReplyOutputDTO(
            chat_id=dto.chat_id,
            query=dto.query,
            context=context,
            answer=answer_text,
        )


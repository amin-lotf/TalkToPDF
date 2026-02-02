from __future__ import annotations

from uuid import UUID

from talk_to_pdf.backend.app.application.common.dto import SearchInputDTO, ContextPackDTO
from talk_to_pdf.backend.app.application.reply.dto import ChatDTO, ReplyInputDTO, MessageDTO, CreateChatInputDTO, \
    CreateMessageInputDTO, ReplyOutputDTO
from talk_to_pdf.backend.app.domain.common.enums import ChatRole
from talk_to_pdf.backend.app.domain.reply.entities import Chat, ChatMessage  # since you put both in entities.py
from talk_to_pdf.backend.app.domain.reply.value_objects import ChatMessageCitations, CitedChunk, GenerateReplyInput
from talk_to_pdf.backend.app.domain.common.value_objects import ChatTurn


def build_search_input_dto(*, dto: ReplyInputDTO, index_id: UUID,chat_messages:list[ChatTurn]) -> SearchInputDTO:
    return SearchInputDTO(
        project_id=dto.project_id,
        owner_id=dto.owner_id,
        index_id=index_id,
        query=dto.query,
        message_history=chat_messages,
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
    citations = None
    # Only create citations for assistant messages with context
    if create_dto.context and create_dto.role == ChatRole.ASSISTANT:
        citations = create_citations_from_context(
            context=create_dto.context,
            top_k=create_dto.top_k or 10,
            rerank_signature=create_dto.rerank_signature,
            prompt_version=create_dto.prompt_version,
            model=create_dto.model,
        )

    return ChatMessage(
        chat_id=create_dto.chat_id,
        role=create_dto.role,
        content=create_dto.content,
        citations=citations,
    )

def message_to_dto(msg: ChatMessage) -> MessageDTO:
    citations_dict = None
    if msg.citations:
        citations_dict = {
            "index_id": str(msg.citations.index_id),
            "embed_signature": msg.citations.embed_signature,
            "metric": msg.citations.metric if isinstance(msg.citations.metric, str) else msg.citations.metric.value,
            "chunks": [
                {
                    "chunk_id": str(chunk.chunk_id),
                    "score": chunk.score,
                    "citation": chunk.citation,
                    "content": chunk.content,
                }
                for chunk in msg.citations.chunks
            ],
            "top_k": msg.citations.top_k,
            "rerank_signature": msg.citations.rerank_signature,
            "prompt_version": msg.citations.prompt_version,
            "model": msg.citations.model,
            "rewritten_query": msg.citations.rewritten_query,
        }

    return MessageDTO(
        id=msg.id,
        chat_id=msg.chat_id,
        role=msg.role,
        content=msg.content,
        created_at=msg.created_at,
        citations=citations_dict,
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


def create_citations_from_context(
    context: ContextPackDTO,
    top_k: int,
    rerank_signature: str | None = None,
    prompt_version: str | None = None,
    model: str | None = None,
) -> ChatMessageCitations:
    """Create ChatMessageCitations from ContextPackDTO for assistant messages."""
    return ChatMessageCitations(
        index_id=context.index_id,
        embed_signature=context.embed_signature,
        metric=context.metric,
        chunks=[
            CitedChunk(
                chunk_id=chunk.chunk_id,
                score=chunk.score,
                citation=chunk.citation or {},
            )
            for chunk in context.chunks
        ],
        top_k=top_k,
        rerank_signature=rerank_signature,
        prompt_version=prompt_version,
        model=model,
        rewritten_query=context.rewritten_query,
    )




def render_context(pack: ContextPackDTO, *, max_chars: int = 12_000) -> str:
    # render chunks as numbered sources
    parts: list[str] = []
    for i, ch in enumerate(pack.chunks, start=1):
        parts.append(f"[{i}] {ch.text}")  # adjust field name
    txt = "\n\n".join(parts)
    return txt[:max_chars]

def map_history(msgs: list[MessageDTO]) -> list[ChatTurn]:
    return [ChatTurn(role=m.role, content=m.content) for m in msgs]

def create_generate_answer_input(query:str,context_pack_dto:ContextPackDTO,message_history:list[ChatTurn],system_prompt:str | None = None) -> GenerateReplyInput:
    return GenerateReplyInput(
        query=query,
        context=render_context(context_pack_dto),
        history=message_history,
        system_prompt=system_prompt,
    )
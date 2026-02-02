from __future__ import annotations

from typing import Callable, AsyncIterator

from talk_to_pdf.backend.app.application.common.interfaces import ContextBuilder
from talk_to_pdf.backend.app.application.reply.dto import ReplyInputDTO, ReplyOutputDTO, CreateMessageInputDTO, \
    GetChatMessagesInputDTO, MessageDTO
from talk_to_pdf.backend.app.application.reply.interfaces import ReplyGenerator
from talk_to_pdf.backend.app.application.reply.mappers import (
    build_search_input_dto,
    create_reply_output_dto,
    create_generate_answer_input, map_history,
)
from talk_to_pdf.backend.app.application.reply.use_cases.create_message import CreateChatMessageUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.get_chat_messages import GetChatMessagesUseCase

from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.retrieval.errors import IndexNotFoundOrForbidden
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden
from talk_to_pdf.backend.app.domain.common.enums import ChatRole


class StreamReplyUseCase:
    def __init__(
            self,
            uow_factory: Callable[[], UnitOfWork],
            ctx_builder_uc: ContextBuilder,
            create_msg_uc: CreateChatMessageUseCase,
            get_chat_messages_uc: GetChatMessagesUseCase,
            reply_generator:ReplyGenerator
    ):
        self._uow_factory = uow_factory
        self._ctx_builder_uc = ctx_builder_uc
        self._create_msg_uc = create_msg_uc
        self._get_chat_messages_uc = get_chat_messages_uc
        self._reply_generator = reply_generator

    async def execute(self, dto: ReplyInputDTO) -> AsyncIterator[str]:
        # 1) Validate index + chat (ownership + same project)
        uow = self._uow_factory()
        async with uow:
            idx = await uow.index_repo.get_latest_ready_by_project_and_owner(
                project_id=dto.project_id,
                owner_id=dto.owner_id,
            )
            if not idx:
                raise IndexNotFoundOrForbidden()

            chat = await uow.chat_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )
            if not chat or chat.project_id != dto.project_id:
                raise ChatNotFoundOrForbidden()

        # 2) Persist user message (through use case)
        await self._create_msg_uc.execute(
            CreateMessageInputDTO(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
                role=ChatRole.USER,
                content=dto.query,
            )
        )

        # 4) Get chat history
        chat_messages_dto = await self._get_chat_messages_uc.execute(
            GetChatMessagesInputDTO(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )
        )

        chat_messages=map_history(chat_messages_dto)

        # 3) Build RAG context
        search_input = build_search_input_dto(dto=dto, index_id=idx.id,chat_messages=chat_messages)
        context = await self._ctx_builder_uc.execute(search_input)



        # 5) Build GenerateReplyInput
        generate_input = create_generate_answer_input(
            query=dto.query,
            context_pack_dto=context,
            message_history=chat_messages,
            system_prompt=None,
        )


        # Accumulate the full answer as we stream
        answer_chunks: list[str] = []

        async for chunk in self._reply_generator.stream_answer(generate_input):
            answer_chunks.append(chunk)
            yield chunk

        # 7) Persist assistant message with citations after streaming completes
        answer_text = "".join(answer_chunks)
        await self._create_msg_uc.execute(
            CreateMessageInputDTO(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
                role=ChatRole.ASSISTANT,
                content=answer_text,
                context=context,
                top_k=dto.top_k,
                rerank_signature=None,
                prompt_version='0.1.0',
                model=self._reply_generator.llm_model,
            )
        )

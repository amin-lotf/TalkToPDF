from __future__ import annotations

from typing import Callable

from talk_to_pdf.backend.app.application.common.interfaces import ContextBuilder
from talk_to_pdf.backend.app.application.reply.dto import ReplyInputDTO, ReplyOutputDTO
from talk_to_pdf.backend.app.application.reply.mappers import build_search_input_dto, \
    create_create_chat_message_input_dto, create_reply_output_dto
from talk_to_pdf.backend.app.application.reply.use_cases.create_message import CreateChatMessageUseCase
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.retrieval.errors import IndexNotFoundOrForbidden
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden
from talk_to_pdf.backend.app.domain.reply.entities import ChatRole


class StreamReplyUseCase:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        ctx_builder_uc: ContextBuilder,
        create_msg_uc: CreateChatMessageUseCase,
    ):
        self._uow_factory = uow_factory
        self._ctx_builder_uc = ctx_builder_uc
        self._create_msg_uc = create_msg_uc

    async def execute(self, dto: ReplyInputDTO) -> ReplyOutputDTO:
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
            create_create_chat_message_input_dto(
                reply_input_dto=dto,
                role=ChatRole.USER,
                content=dto.query,
            )
        )

        # 3) Build RAG context
        search_input = build_search_input_dto(dto=dto, index_id=idx.id)
        context = await self._ctx_builder_uc.execute(search_input)

        # 4) LLM call (stub for now)
        answer_text = "LLM response"

        # 5) Persist assistant message (through use case)
        await self._create_msg_uc.execute(
            create_create_chat_message_input_dto(
                reply_input_dto=dto,
                role=ChatRole.ASSISTANT,
                content=answer_text,
            )
        )
        return create_reply_output_dto(
            dto=dto,
            answer_text=answer_text,
            context=context,
        )

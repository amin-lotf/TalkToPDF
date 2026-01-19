from __future__ import annotations

from typing import Callable

from talk_to_pdf.backend.app.application.common.interfaces import ContextBuilder
from talk_to_pdf.backend.app.application.reply.dto import ReplyInputDTO, ReplyOutputDTO
from talk_to_pdf.backend.app.application.reply.mappers import build_search_input_dto
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.retrieval.errors import IndexNotFoundOrForbidden
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden  # create


class StreamReplyUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], ctx_builder_uc: ContextBuilder):
        self._uow_factory = uow_factory
        self._ctx_builder_uc = ctx_builder_uc

    async def execute(self, dto: ReplyInputDTO) -> ReplyOutputDTO:
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
                # important: ensure chat belongs to the same project
                raise ChatNotFoundOrForbidden()

        search_input = build_search_input_dto(dto=dto, index_id=idx.id)
        context = await self._ctx_builder_uc.execute(search_input)

        return ReplyOutputDTO(chat_id=dto.chat_id, query=dto.query, context=context, answer="")

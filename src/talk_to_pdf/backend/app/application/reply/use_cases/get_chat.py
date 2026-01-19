from __future__ import annotations

from typing import Callable

from talk_to_pdf.backend.app.application.reply.dto import ChatDTO, GetChatInputDTO
from talk_to_pdf.backend.app.application.reply.mappers import chat_domain_to_dto
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden


class GetChatUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, dto: GetChatInputDTO) -> ChatDTO:
        uow = self._uow_factory()
        async with uow:
            chat = await uow.chat_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )
            if not chat:
                raise ChatNotFoundOrForbidden()

        return chat_domain_to_dto(chat)

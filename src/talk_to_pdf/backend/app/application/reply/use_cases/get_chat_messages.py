from __future__ import annotations

from typing import Callable

from talk_to_pdf.backend.app.application.reply.dto import GetChatMessagesInputDTO, MessageDTO
from talk_to_pdf.backend.app.application.reply.mappers import message_to_dto
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden


class GetChatMessagesUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, dto: GetChatMessagesInputDTO) -> list[MessageDTO]:
        uow = self._uow_factory()
        async with uow:
            # enforce ownership (avoid leaking whether the chat exists)
            chat = await uow.chat_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )
            if not chat:
                raise ChatNotFoundOrForbidden()

            msgs = await uow.chat_message_repo.list_recent_by_owner_and_chat(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
                limit=int(dto.limit),
            )

        return [message_to_dto(m) for m in msgs]

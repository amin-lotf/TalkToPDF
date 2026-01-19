from __future__ import annotations

from typing import Callable
from talk_to_pdf.backend.app.application.reply.dto import CreateMessageInputDTO, MessageDTO
from talk_to_pdf.backend.app.application.reply.mappers import message_to_dto, create_chat_message_domain
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden




class CreateChatMessageUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, dto: CreateMessageInputDTO) -> MessageDTO:
        uow = self._uow_factory()
        async with uow:
            chat = await uow.chat_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )
            if not chat:
                raise ChatNotFoundOrForbidden()

            msg =create_chat_message_domain(dto)
            await uow.chat_message_repo.add(msg)

            # keep chat ordering / "last active" accurate
            # (works nicely for sidebar sorting)
            chat2 = chat.touch()
            await uow.chat_repo.add(chat2)  # ⚠️ only if your repo 'add' is upsert-like
            # If your repo has update(), prefer that:
            # await uow.chat_repo.update(chat2)


        return message_to_dto(msg)

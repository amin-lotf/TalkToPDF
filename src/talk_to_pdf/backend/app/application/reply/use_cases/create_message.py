from __future__ import annotations

from talk_to_pdf.backend.app.application.reply.dto import CreateMessageInputDTO, MessageDTO
from talk_to_pdf.backend.app.application.reply.mappers import message_to_dto, create_chat_message_domain
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden




class CreateChatMessageUseCase:
    def __init__(self, uow_factory):
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

            msg = create_chat_message_domain(dto)
            await uow.chat_message_repo.add(msg)  # repo will touch chat

        return message_to_dto(msg)

from __future__ import annotations

from typing import Callable

from talk_to_pdf.backend.app.application.reply.dto import DeleteChatInputDTO
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden  # create this domain error


class DeleteChatUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, dto: DeleteChatInputDTO) -> None:
        uow = self._uow_factory()
        async with uow:
            # delete messages first (if no FK cascade)
            await uow.chat_message_repo.delete_by_owner_and_chat(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )

            deleted = await uow.chat_repo.delete_by_owner_and_id(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )
            if not deleted:
                raise ChatNotFoundOrForbidden()


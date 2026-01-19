from __future__ import annotations

from typing import Callable

from talk_to_pdf.backend.app.application.reply.dto import ChatDTO, ListChatsInputDTO
from talk_to_pdf.backend.app.application.reply.mappers import chat_domain_to_dto
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork


class ListChatsUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, dto: ListChatsInputDTO) -> list[ChatDTO]:
        uow = self._uow_factory()
        async with uow:
            chats = await uow.chat_repo.list_by_owner_and_project(
                owner_id=dto.owner_id,
                project_id=dto.project_id,
                limit=int(dto.limit),
                offset=int(dto.offset),
            )
        return [chat_domain_to_dto(c) for c in chats]

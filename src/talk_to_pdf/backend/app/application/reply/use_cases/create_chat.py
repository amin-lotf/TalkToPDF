from __future__ import annotations

from typing import Callable
from talk_to_pdf.backend.app.application.reply.dto import ChatDTO, CreateChatInputDTO
from talk_to_pdf.backend.app.application.reply.mappers import chat_domain_to_dto, create_chat_domain
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.projects.errors import ProjectNotFound


class CreateChatUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, dto: CreateChatInputDTO) -> ChatDTO:
        uow = self._uow_factory()
        async with uow:
            project = await uow.project_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                project_id=dto.project_id,
            )
            if not project:
                raise ProjectNotFound(project_id=str(dto.project_id))

            chat = create_chat_domain(dto)
            await uow.chat_repo.add(chat)

        return chat_domain_to_dto(chat)

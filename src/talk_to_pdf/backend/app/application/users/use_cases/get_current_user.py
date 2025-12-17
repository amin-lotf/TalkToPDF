from __future__ import annotations
from uuid import UUID
from talk_to_pdf.backend.app.application.users import CurrentUserDTO
from talk_to_pdf.backend.app.application.users.mappers import current_domain_to_output_dto
from talk_to_pdf.backend.app.domain.users import UserNotFoundError
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork


class GetCurrentUserUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID) -> CurrentUserDTO:
        async with self._uow:
            user = await self._uow.user_repo.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError()
            return current_domain_to_output_dto(user)
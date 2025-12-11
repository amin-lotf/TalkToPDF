from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID

from talk_to_pdf.backend.app.application.users import CurrentUserDTO
from talk_to_pdf.backend.app.application.users.mappers import current_domain_to_output_dto
from talk_to_pdf.backend.app.domain.users import UserNotFoundError
from talk_to_pdf.backend.app.domain.users.repositories import UserRepository




class GetCurrentUserUseCase:
    def __init__(
            self,
            user_repo: UserRepository
    ) -> None:
        self._user_repo = user_repo

    async def execute(self, user_id: UUID) -> CurrentUserDTO:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return current_domain_to_output_dto(user)

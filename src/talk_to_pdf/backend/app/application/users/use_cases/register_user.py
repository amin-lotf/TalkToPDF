from __future__ import annotations

from talk_to_pdf.backend.app.application.users import RegisterUserInput, RegisterUserOutput
from talk_to_pdf.backend.app.application.users.mappers import (
    register_domain_to_output_dto,
    register_input_dto_to_domain,
)
from talk_to_pdf.backend.app.application.users.interfaces import PasswordHasher
from talk_to_pdf.backend.app.domain.users import RegistrationError
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork


class RegisterUserUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        self._uow = uow
        self._password_hasher = password_hasher

    async def execute(self, data: RegisterUserInput) -> RegisterUserOutput:
        async with self._uow:
            existing = await self._uow.user_repo.get_by_email(data.email)
            if existing is not None:
                raise RegistrationError(f"Email {data.email} is already in use")

            hashed = self._password_hasher.hash(data.password)
            user = register_input_dto_to_domain(data, hashed)

            saved = await self._uow.user_repo.add(user)
            return register_domain_to_output_dto(saved)

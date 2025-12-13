from __future__ import annotations
from typing import Protocol
from talk_to_pdf.backend.app.application.users import RegisterUserInput, RegisterUserOutput
from talk_to_pdf.backend.app.application.users.mappers import register_input_dto_to_domain, register_domain_to_output_dto
from talk_to_pdf.backend.app.application.users.use_cases.protocols import PasswordHasher
from talk_to_pdf.backend.app.domain.users import RegistrationError
from talk_to_pdf.backend.app.domain.users.repositories import UserRepository





class RegisterUserUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    async def execute(self, data: RegisterUserInput) -> RegisterUserOutput:
        existing = await self._user_repo.get_by_email(data.email)
        if existing is not None:
            raise RegistrationError(f"Email {data.email} is already in use")
        hashed = self._password_hasher.hash(data.password)
        user = register_input_dto_to_domain(data,hashed)
        saved = await self._user_repo.add(user)
        return register_domain_to_output_dto(saved)

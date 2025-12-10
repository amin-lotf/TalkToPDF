from __future__ import annotations
from typing import Protocol
from talk_to_pdf.backend.app.application.users import RegisterUserInput, RegisterUserOutput, dto_to_domain, \
    domain_to_dto
from talk_to_pdf.backend.app.domain.users import UserRepository, EmailAlreadyRegisteredError, User, UserEmail


class PasswordHasher(Protocol):
    def hash(self, raw_password: str) -> str:
        ...


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
            raise EmailAlreadyRegisteredError(f"Email {data.email} is already in use")
        hashed = self._password_hasher.hash(data.password)
        user = dto_to_domain(data)
        user.hashed_password = hashed
        saved = await self._user_repo.add(user)
        return domain_to_dto(saved)

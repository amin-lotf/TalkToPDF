from __future__ import annotations
from talk_to_pdf.backend.app.application.users import LoginUserInputDTO, LoginUserOutputDTO
from talk_to_pdf.backend.app.application.users.mappers import login_domain_to_output_dto
from talk_to_pdf.backend.app.application.users.use_cases.protocols import PasswordHasher
from talk_to_pdf.backend.app.domain.users.erorrs import InvalidCredentialsError, InactiveUserError
from talk_to_pdf.backend.app.domain.users.repositories import UserRepository


class LoginUserUseCase:
    def __init__(
            self,
            user_repo: UserRepository,
            password_hasher: PasswordHasher,
    ) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    async def execute(self, dto: LoginUserInputDTO) -> LoginUserOutputDTO:
        # 1) load user by email
        user = await self._user_repo.get_by_email(dto.email)
        if user is None:
            raise InvalidCredentialsError()

        # 2) check password
        if not self._password_hasher.verify(dto.password, user.hashed_password):
            raise InvalidCredentialsError()

        # 3) check an active flag
        if not user.is_active:
            raise InactiveUserError()

        # 4) return a pure DTO (no HTTP, no JWT here)
        return login_domain_to_output_dto(user)

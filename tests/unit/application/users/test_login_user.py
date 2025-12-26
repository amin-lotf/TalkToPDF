import pytest

from talk_to_pdf.backend.app.application.users import LoginUserInputDTO
from talk_to_pdf.backend.app.application.users.use_cases.login_user import LoginUserUseCase
from talk_to_pdf.backend.app.domain.users import User
from talk_to_pdf.backend.app.domain.users.value_objects import UserEmail
from talk_to_pdf.backend.app.domain.users.erorrs import InvalidCredentialsError, InactiveUserError


pytestmark = pytest.mark.asyncio


class PlaintextTestHasher:
    """
    Fast + deterministic for unit tests.
    You still test DB/UoW/repository integration; you’re not paying bcrypt cost.
    """
    def hash(self, raw_password: str) -> str:
        return raw_password

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        return raw_password == hashed_password


async def seed_user(*, uow, email: str, name: str, hashed_password: str, is_active: bool = True):
    """
    Inserts a user using your real UoW + repo so the DB is truly exercised.
    """
    async with uow:
        user = User(
            email=UserEmail(email),
            name=name,
            hashed_password=hashed_password,
            is_active=is_active,
        )
        await uow.user_repo.add(user)
    return user


async def test_login_success_returns_output_dto(uow):
    password_hasher = PlaintextTestHasher()
    await seed_user(
        uow=uow,
        email="amin@example.com",
        name="Amin",
        hashed_password=password_hasher.hash("secret123"),
        is_active=True,
    )

    use_case = LoginUserUseCase(uow=uow, password_hasher=password_hasher)
    dto = LoginUserInputDTO(email="amin@example.com", password="secret123")

    out = await use_case.execute(dto)

    assert out.email == "amin@example.com"
    assert out.id is not None
    # Assuming output DTO has is_active or other fields you want to verify
    assert out.is_active is True


async def test_login_unknown_email_raises_invalid_credentials(uow):
    use_case = LoginUserUseCase(uow=uow, password_hasher=PlaintextTestHasher())
    dto = LoginUserInputDTO(email="missing@example.com", password="whatever")

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(dto)


async def test_login_wrong_password_raises_invalid_credentials(uow):
    password_hasher = PlaintextTestHasher()
    await seed_user(
        uow=uow,
        email="wrongpass@example.com",
        name="Amin",
        hashed_password=password_hasher.hash("correct"),
        is_active=True,
    )

    use_case = LoginUserUseCase(uow=uow, password_hasher=password_hasher)
    dto = LoginUserInputDTO(email="wrongpass@example.com", password="incorrect")

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(dto)


async def test_login_inactive_user_raises_inactive_user_error(uow):
    password_hasher = PlaintextTestHasher()
    await seed_user(
        uow=uow,
        email="inactive@example.com",
        name="Amin",
        hashed_password=password_hasher.hash("secret"),
        is_active=False,
    )

    use_case = LoginUserUseCase(uow=uow, password_hasher=password_hasher)
    dto = LoginUserInputDTO(email="inactive@example.com", password="secret")

    with pytest.raises(InactiveUserError):
        await use_case.execute(dto)



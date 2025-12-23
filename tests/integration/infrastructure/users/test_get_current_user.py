import pytest
from uuid import uuid4

from talk_to_pdf.backend.app.application.users.use_cases.get_current_user import GetCurrentUserUseCase
from talk_to_pdf.backend.app.domain.users import User, UserNotFoundError
from talk_to_pdf.backend.app.domain.users.value_objects import UserEmail


pytestmark = pytest.mark.asyncio


async def seed_user(*, uow, email: str = "amin@example.com", name: str = "Amin", is_active: bool = True) -> User:
    """
    Insert a user via the real UoW/repository (true integration with DB).
    """
    async with uow:
        user = User(
            email=UserEmail(email),
            name=name,
            hashed_password="hashed-password-for-tests",
            is_active=is_active,
        )
        await uow.user_repo.add(user)
    return user


async def test_get_current_user_returns_dto(uow):
    saved = await seed_user(uow=uow, email="current@example.com", name="Amin")

    use_case = GetCurrentUserUseCase(uow=uow)
    out = await use_case.execute(saved.id)

    # Assert only what CurrentUserDTO guarantees.
    assert out.id == saved.id
    assert out.email == "current@example.com"
    assert out.name == "Amin"
    assert out.is_active is True


async def test_get_current_user_not_found_raises(uow):
    use_case = GetCurrentUserUseCase(uow=uow)

    with pytest.raises(UserNotFoundError):
        await use_case.execute(uuid4())

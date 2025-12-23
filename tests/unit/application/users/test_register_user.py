import pytest

from talk_to_pdf.backend.app.application.users import RegisterUserInput
from talk_to_pdf.backend.app.application.users.use_cases.register_user import RegisterUserUseCase
from talk_to_pdf.backend.app.domain.users import RegistrationError


pytestmark = pytest.mark.asyncio


async def test_register_user_happy_path(uow, hasher):
    use_case = RegisterUserUseCase(uow=uow, password_hasher=hasher)

    out = await use_case.execute(
        RegisterUserInput(
            email="amin@example.com",
            name="Amin",
            password="secret123",
        )
    )

    assert out.email == "amin@example.com"
    assert out.name == "Amin"
    assert out.id is not None
    assert out.created_at is not None

    # because commit happens in __aexit__
    assert uow.committed is True
    assert uow.rolled_back is False

    saved = await uow.user_repo.get_by_email("amin@example.com")
    assert saved is not None
    assert saved.hashed_password == "hashed::secret123"
    assert saved.is_active is True


async def test_register_user_duplicate_email_rolls_back(uow, hasher):
    use_case = RegisterUserUseCase(uow=uow, password_hasher=hasher)

    await use_case.execute(
        RegisterUserInput(email="amin@example.com", name="Amin", password="x")
    )

    with pytest.raises(RegistrationError):
        await use_case.execute(
            RegisterUserInput(email="amin@example.com", name="Someone", password="y")
        )

    assert uow.rolled_back is True

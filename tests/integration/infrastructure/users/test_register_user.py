import pytest
from talk_to_pdf.backend.app.application.users import RegisterUserInput
from talk_to_pdf.backend.app.application.users.use_cases import RegisterUserUseCase
from talk_to_pdf.backend.app.core.security import BcryptPasswordHasher

pytestmark = pytest.mark.asyncio

async def test_register_user_use_case_integration(uow):
    use_case = RegisterUserUseCase(uow=uow, password_hasher=BcryptPasswordHasher())

    user_input = RegisterUserInput(
        email="test@example.com",
        name="Test User",
        password="securepassword123",
    )

    result = await use_case.execute(user_input)

    assert result.email == "test@example.com"
    assert result.id is not None

    saved_user = await uow.user_repo.get_by_email("test@example.com")
    assert saved_user is not None
    assert saved_user.name == "Test User"

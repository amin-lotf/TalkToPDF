import pytest
from uuid import uuid4

from talk_to_pdf.backend.app.domain.users import User, RegistrationError
from talk_to_pdf.backend.app.domain.users.value_objects import UserEmail
from talk_to_pdf.backend.app.infrastructure.users.repositories import SqlAlchemyUserRepository

pytestmark = pytest.mark.asyncio


def make_user(*, email: str, name: str = "Amin") -> User:
    """
    Single factory for domain-correct User creation.
    Change ONLY here if the domain evolves.
    """
    return User(
        email=UserEmail(email),
        name=name,
        hashed_password="hashed-password-for-tests",
    )


async def test_add_persists_and_get_by_email(session):
    repo = SqlAlchemyUserRepository(session)

    user = make_user(email="amin@example.com")
    saved = await repo.add(user)

    found = await repo.get_by_email("amin@example.com")

    assert found is not None
    assert found.id == saved.id
    assert found.email == user.email
    assert found.name == "Amin"
    assert found.is_active is True


async def test_get_by_email_returns_none_when_missing(session):
    repo = SqlAlchemyUserRepository(session)

    found = await repo.get_by_email("missing@example.com")

    assert found is None


async def test_get_by_id_returns_user(session):
    repo = SqlAlchemyUserRepository(session)

    user = make_user(email="byid@example.com")
    saved = await repo.add(user)

    found = await repo.get_by_id(saved.id)

    assert found is not None
    assert found.id == saved.id
    assert found.email == user.email


async def test_get_by_id_returns_none_when_missing(session):
    repo = SqlAlchemyUserRepository(session)

    found = await repo.get_by_id(uuid4())

    assert found is None


async def test_add_duplicate_email_raises_registration_error(session):
    repo = SqlAlchemyUserRepository(session)

    await repo.add(make_user(email="dup@example.com"))

    with pytest.raises(RegistrationError) as exc:
        await repo.add(make_user(email="dup@example.com"))

    assert "dup@example.com" in str(exc.value)

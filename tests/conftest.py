import pytest

from tests.unit.fakes.hasher import FakePasswordHasher
from tests.unit.fakes.uow import FakeUnitOfWork


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def hasher() -> FakePasswordHasher:
    return FakePasswordHasher()

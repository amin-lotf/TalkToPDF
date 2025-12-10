from __future__ import annotations
from typing import Protocol, Optional
from uuid import UUID
from .entities import User


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> Optional[User]:
        ...

    async def add(self, user: User) -> User:
        ...

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        ...

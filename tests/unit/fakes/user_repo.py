from __future__ import annotations

from dataclasses import replace
from typing import Optional
from uuid import UUID

from talk_to_pdf.backend.app.domain.users.entities import User
from talk_to_pdf.backend.app.domain.users.repositories import UserRepository  # adjust import path


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, User] = {}
        self._by_email: dict[str, User] = {}

    async def get_by_email(self, email: str) -> Optional[User]:
        return self._by_email.get(email.lower())

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self._by_id.get(user_id)

    async def add(self, user: User) -> User:
        # Persist exactly what you received (frozen dataclass)
        # Normalize email string key
        email_str = str(user.email).lower() if hasattr(user.email, "__str__") else user.email.value.lower()
        self._by_id[user.id] = user
        self._by_email[email_str] = user
        return user

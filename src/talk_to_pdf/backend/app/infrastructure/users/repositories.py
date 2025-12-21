# app/infrastructure/auth/repositories.py
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.domain.users import User, RegistrationError
from talk_to_pdf.backend.app.infrastructure.users.mappers import user_model_to_domain, user_domain_to_model
from talk_to_pdf.backend.app.infrastructure.users.models import UserModel




class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        model: Optional[UserModel] = result.scalar_one_or_none()
        if model is None:
            return None
        return user_model_to_domain(model)

    async def add(self, user: User) -> User:
        model = user_domain_to_model(user)
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as e:
            # most likely UNIQUE(email)
            raise RegistrationError(f"Email {user.email} already exists") from e
        await self._session.refresh(model)
        return user_model_to_domain(model)

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model: Optional[UserModel] = result.scalar_one_or_none()
        if model is None:
            return None
        return user_model_to_domain(model)

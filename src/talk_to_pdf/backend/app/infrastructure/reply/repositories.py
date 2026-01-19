from __future__ import annotations

from datetime import datetime
from typing import Iterable
from uuid import UUID
from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.domain.reply import Chat, ChatMessage
from talk_to_pdf.backend.app.infrastructure.db.models import ProjectModel,ChatModel, ChatMessageModel
from talk_to_pdf.backend.app.infrastructure.reply.mappers import chat_domain_to_model, chat_model_to_domain, \
    message_domain_to_model, message_model_to_domain


class SqlAlchemyChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, chat: Chat) -> None:
        self._session.add(chat_domain_to_model(chat))
        await self._session.flush()

    async def get_by_owner_and_id(self, *, owner_id: UUID, chat_id: UUID) -> Chat | None:
        """
        Ownership via Project.owner_id.
        """
        stmt = (
            select(ChatModel)
            .join(ProjectModel, ProjectModel.id == ChatModel.project_id)
            .where(ChatModel.id == chat_id)
            .where(ProjectModel.owner_id == owner_id)
        )
        model = await self._session.scalar(stmt)
        return chat_model_to_domain(model) if model else None

    async def list_by_owner_and_project(
            self,
            *,
            owner_id: UUID,
            project_id: UUID,
            limit: int = 50,
            offset: int = 0,
    ) -> list[Chat]:
        stmt = (
            select(ChatModel)
            .join(ProjectModel, ProjectModel.id == ChatModel.project_id)
            .where(ProjectModel.owner_id == owner_id)
            .where(ProjectModel.id == project_id)
            .order_by(desc(ChatModel.updated_at))
            .limit(int(limit))
            .offset(int(offset))
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [chat_model_to_domain(r) for r in rows]

    async def delete_by_owner_and_id(self, *, owner_id: UUID, chat_id: UUID) -> bool:
        """
        True if deleted, False if not found (or not owned).
        """
        # This is the most reliable cross-DB pattern: select ids then delete.
        # It avoids "DELETE ... USING" portability issues.
        owned_stmt = (
            select(ChatModel.id)
            .join(ProjectModel, ProjectModel.id == ChatModel.project_id)
            .where(ChatModel.id == chat_id)
            .where(ProjectModel.owner_id == owner_id)
        )
        owned_id = (await self._session.execute(owned_stmt)).scalar_one_or_none()
        if owned_id is None:
            return False

        del_stmt = delete(ChatModel).where(ChatModel.id == owned_id)
        result = await self._session.execute(del_stmt)
        # rowcount should be 1 here, but keep it robust:
        return bool(result.rowcount and result.rowcount > 0)


class SqlAlchemyChatMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: ChatMessage) -> None:
        self._session.add(message_domain_to_model(message))

        await self._session.execute(
            update(ChatModel)
            .where(ChatModel.id == message.chat_id)
            .values(updated_at=message.created_at)
        )

        await self._session.flush()

    async def add_many(self, messages: Iterable[ChatMessage]) -> None:
        msgs = list(messages)
        if not msgs:
            return
        self._session.add_all([message_domain_to_model(m) for m in msgs])
        await self._session.flush()

    async def list_recent_by_owner_and_chat(
            self,
            *,
            owner_id: UUID,
            chat_id: UUID,
            limit: int = 20,
            before: datetime | None = None,
    ) -> list[ChatMessage]:
        """
        Return messages ordered oldest -> newest (LLM-friendly).

        Efficient pattern:
        - fetch newest N (desc)
        - reverse in python
        This keeps correct "recent window" semantics.
        """
        stmt = (
            select(ChatMessageModel)
            .join(ChatModel, ChatModel.id == ChatMessageModel.chat_id)
            .join(ProjectModel, ProjectModel.id == ChatModel.project_id)
            .where(ChatMessageModel.chat_id == chat_id)
            .where(ProjectModel.owner_id == owner_id)
        )

        if before is not None:
            stmt = stmt.where(ChatMessageModel.created_at < before)

        stmt = stmt.order_by(desc(ChatMessageModel.created_at)).limit(int(limit))

        rows = (await self._session.execute(stmt)).scalars().all()

        # rows are newest -> oldest; convert to oldest -> newest
        rows = list(reversed(rows))
        return [message_model_to_domain(r) for r in rows]

    async def delete_by_owner_and_chat(self, *, owner_id: UUID, chat_id: UUID) -> int:
        """
        Returns number of deleted messages.
        """
        # Validate ownership by resolving chat id owned by owner_id
        owned_stmt = (
            select(ChatModel.id)
            .join(ProjectModel, ProjectModel.id == ChatModel.project_id)
            .where(ChatModel.id == chat_id)
            .where(ProjectModel.owner_id == owner_id)
        )
        owned_chat_id = (await self._session.execute(owned_stmt)).scalar_one_or_none()
        if owned_chat_id is None:
            return 0

        del_stmt = delete(ChatMessageModel).where(ChatMessageModel.chat_id == owned_chat_id)
        result = await self._session.execute(del_stmt)
        return int(result.rowcount or 0)

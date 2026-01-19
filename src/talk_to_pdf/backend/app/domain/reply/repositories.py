from __future__ import annotations

from datetime import datetime
from typing import Iterable, Protocol
from uuid import UUID

from talk_to_pdf.backend.app.domain.reply import Chat, ChatMessage


class ChatRepository(Protocol):
    async def add(self, chat: Chat) -> None:
        ...

    async def get_by_owner_and_id(self, *, owner_id: UUID, chat_id: UUID) -> Chat | None:
        ...

    async def list_by_owner_and_project(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Chat]:
        """
        Returns chats ordered by updated_at desc (implementation detail),
        but domain doesn't care about exact ordering rules.
        """
        ...

    async def delete_by_owner_and_id(self, *, owner_id: UUID, chat_id: UUID) -> bool:
        """
        True if deleted, False if not found (or not owned).
        """
        ...


class ChatMessageRepository(Protocol):
    async def add(self, message: ChatMessage) -> None:
        ...

    async def add_many(self, messages: Iterable[ChatMessage]) -> None:
        ...

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
        """
        ...

    async def delete_by_owner_and_chat(self, *, owner_id: UUID, chat_id: UUID) -> int:
        """
        Returns number of deleted messages.
        """
        ...

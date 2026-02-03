from __future__ import annotations

from typing import Callable
from uuid import UUID

from talk_to_pdf.backend.app.application.reply.dto import GetChatMessagesInputDTO, MessageDTO
from talk_to_pdf.backend.app.application.reply.mappers import message_to_dto
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden
from talk_to_pdf.backend.app.domain.reply.value_objects import CitedChunk


class GetChatMessagesUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, dto: GetChatMessagesInputDTO) -> list[MessageDTO]:
        uow = self._uow_factory()
        async with uow:
            # enforce ownership (avoid leaking whether the chat exists)
            chat = await uow.chat_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )
            if not chat:
                raise ChatNotFoundOrForbidden()

            msgs = await uow.chat_message_repo.list_recent_by_owner_and_chat(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
                limit=int(dto.limit),
            )

            # Populate chunk content for messages with citations
            updated_msgs = []
            for msg in msgs:
                if msg.citations and msg.citations.chunks:
                    chunk_ids = [chunk.chunk_id for chunk in msg.citations.chunks]
                    chunks = await uow.chunk_repo.get_many_by_ids_for_index(
                        index_id=msg.citations.index_id,
                        ids=chunk_ids,
                    )

                    # Create a mapping of chunk_id to chunk text
                    chunk_map = {chunk.id: chunk.text for chunk in chunks}

                    # Update citations with chunk content
                    updated_chunks = [
                        CitedChunk(
                            chunk_id=cited_chunk.chunk_id,
                            score=cited_chunk.score,
                            citation=cited_chunk.citation,
                            content=chunk_map.get(cited_chunk.chunk_id),
                        )
                        for cited_chunk in msg.citations.chunks
                    ]

                    # Create new citations with updated chunks
                    from talk_to_pdf.backend.app.domain.reply.value_objects import ChatMessageCitations
                    from talk_to_pdf.backend.app.domain.reply.entities import ChatMessage
                    updated_citations = ChatMessageCitations(
                        index_id=msg.citations.index_id,
                        embed_signature=msg.citations.embed_signature,
                        metric=msg.citations.metric,
                        chunks=updated_chunks,
                        top_k=msg.citations.top_k,
                        rerank_signature=msg.citations.rerank_signature,
                        prompt_version=msg.citations.prompt_version,
                        model=msg.citations.model,
                        rewritten_query=msg.citations.rewritten_queries,
                    )

                    # Create new message with updated citations (dataclass is frozen)
                    updated_msg = ChatMessage(
                        id=msg.id,
                        chat_id=msg.chat_id,
                        role=msg.role,
                        content=msg.content,
                        created_at=msg.created_at,
                        citations=updated_citations,
                        metrics=msg.metrics,
                    )
                    updated_msgs.append(updated_msg)
                else:
                    updated_msgs.append(msg)

        return [message_to_dto(m) for m in updated_msgs]

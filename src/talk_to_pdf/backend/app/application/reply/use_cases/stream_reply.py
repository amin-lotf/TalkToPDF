from __future__ import annotations

import time
from typing import Callable, AsyncIterator

from talk_to_pdf.backend.app.application.common.interfaces import ContextBuilder
from talk_to_pdf.backend.app.application.reply.dto import ReplyInputDTO, ReplyOutputDTO, CreateMessageInputDTO, \
    GetChatMessagesInputDTO, MessageDTO
from talk_to_pdf.backend.app.application.reply.interfaces import ReplyGenerator
from talk_to_pdf.backend.app.application.reply.mappers import (
    build_search_input_dto,
    create_reply_output_dto,
    create_generate_answer_input, map_history,
)
from talk_to_pdf.backend.app.application.reply.use_cases.create_message import CreateChatMessageUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.get_chat_messages import GetChatMessagesUseCase

from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.retrieval.errors import IndexNotFoundOrForbidden
from talk_to_pdf.backend.app.domain.reply.errors import ChatNotFoundOrForbidden
from talk_to_pdf.backend.app.domain.common.enums import ChatRole
from talk_to_pdf.backend.app.domain.reply.metrics import ReplyMetrics, TokenMetrics, LatencyMetrics
from talk_to_pdf.backend.app.infrastructure.common.token_counter import count_tokens


class StreamReplyUseCase:
    def __init__(
            self,
            uow_factory: Callable[[], UnitOfWork],
            ctx_builder_uc: ContextBuilder,
            create_msg_uc: CreateChatMessageUseCase,
            get_chat_messages_uc: GetChatMessagesUseCase,
            reply_generator:ReplyGenerator
    ):
        self._uow_factory = uow_factory
        self._ctx_builder_uc = ctx_builder_uc
        self._create_msg_uc = create_msg_uc
        self._get_chat_messages_uc = get_chat_messages_uc
        self._reply_generator = reply_generator

    async def execute(self, dto: ReplyInputDTO) -> AsyncIterator[str]:
        # Track latencies
        query_rewrite_latency: float | None = None
        retrieval_latency: float | None = None
        reply_generation_latency: float | None = None
        rewritten_question_tokens = 0

        # 1) Validate index + chat (ownership + same project)
        uow = self._uow_factory()
        async with uow:
            idx = await uow.index_repo.get_latest_ready_by_project_and_owner(
                project_id=dto.project_id,
                owner_id=dto.owner_id,
            )
            if not idx:
                raise IndexNotFoundOrForbidden()

            chat = await uow.chat_repo.get_by_owner_and_id(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )
            if not chat or chat.project_id != dto.project_id:
                raise ChatNotFoundOrForbidden()

        # 2) Persist user message (through use case)
        await self._create_msg_uc.execute(
            CreateMessageInputDTO(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
                role=ChatRole.USER,
                content=dto.query,
            )
        )

        # 4) Get chat history
        chat_messages_dto = await self._get_chat_messages_uc.execute(
            GetChatMessagesInputDTO(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
            )
        )

        chat_messages=map_history(chat_messages_dto)

        # 3) Build RAG context (includes query rewriting + retrieval)
        retrieval_start = time.time()
        search_input = build_search_input_dto(dto=dto, index_id=idx.id,chat_messages=chat_messages)
        context = await self._ctx_builder_uc.execute(search_input)
        retrieval_latency = time.time() - retrieval_start

        # Count rewritten question tokens if available
        if context.rewritten_query:
            rewritten_question_tokens = count_tokens(context.rewritten_query, model=self._reply_generator.llm_model)

        # 5) Build GenerateReplyInput
        generate_input = create_generate_answer_input(
            query=dto.query,
            context_pack_dto=context,
            message_history=chat_messages,
            system_prompt=None,
        )


        # Accumulate the full answer as we stream
        answer_chunks: list[str] = []

        # 6) Stream reply with latency tracking
        reply_start = time.time()
        async for chunk in self._reply_generator.stream_answer(generate_input):
            answer_chunks.append(chunk)
            yield chunk
        reply_generation_latency = time.time() - reply_start

        # 7) Collect metrics
        stream_metrics = self._reply_generator.get_last_metrics()

        metrics = None
        if stream_metrics:
            token_metrics = TokenMetrics(
                system=stream_metrics.prompt_breakdown.system,
                history=stream_metrics.prompt_breakdown.history,
                rewritten_question=rewritten_question_tokens,
                context=stream_metrics.prompt_breakdown.context,
                question=stream_metrics.prompt_breakdown.question,
            )

            latency_metrics = LatencyMetrics(
                query_rewriting=None,  # Query rewriting is part of retrieval in current setup
                retrieval=retrieval_latency,
                reply_generation=reply_generation_latency,
            )

            metrics = ReplyMetrics(
                prompt_tokens=token_metrics,
                completion_tokens=stream_metrics.completion_tokens,
                latency=latency_metrics,
            )

        # 8) Persist assistant message with citations after streaming completes
        answer_text = "".join(answer_chunks)
        await self._create_msg_uc.execute(
            CreateMessageInputDTO(
                owner_id=dto.owner_id,
                chat_id=dto.chat_id,
                role=ChatRole.ASSISTANT,
                content=answer_text,
                context=context,
                top_k=dto.top_k,
                rerank_signature=None,
                prompt_version='0.1.0',
                model=self._reply_generator.llm_model,
                metrics=metrics,
            )
        )

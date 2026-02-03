from functools import lru_cache
from typing import Annotated, Callable

from fastapi import Depends

from talk_to_pdf.backend.app.application.common.interfaces import ContextBuilder
from talk_to_pdf.backend.app.application.reply.use_cases.create_message import CreateChatMessageUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.stream_reply import StreamReplyUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.create_chat import CreateChatUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.get_chat import GetChatUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.list_chats import ListChatsUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.delete_chat import DeleteChatUseCase
from talk_to_pdf.backend.app.application.reply.use_cases.get_chat_messages import GetChatMessagesUseCase
from talk_to_pdf.backend.app.application.retrieval.use_cases.build_index_context import BuildIndexContextUseCase
from talk_to_pdf.backend.app.infrastructure.retrieval.merger.mergers import DeterministicRetrievalResultMerger
from talk_to_pdf.backend.app.core.config import settings
from talk_to_pdf.backend.app.core.deps import get_uow_factory, get_reply_generation_config, get_query_rewrite_config, \
    get_reranker_config
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.common.value_objects import ReplyGenerationConfig, QueryRewriteConfig, \
    RerankerConfig
from talk_to_pdf.backend.app.infrastructure.common.embedders.factory_openai_langchain import OpenAIEmbedderFactory
from talk_to_pdf.backend.app.infrastructure.reply.query_rewriter.factory_openai_rewriter import \
    OpenAILlmQueryRewriterFactory
from talk_to_pdf.backend.app.infrastructure.reply.query_rewriter.openai_query_rewriter import OpenAIQueryRewriter
from talk_to_pdf.backend.app.infrastructure.reply.reply_generator.factory_openai_reply_generator import \
    OpenAILlmReplyGeneratorFactory
from talk_to_pdf.backend.app.infrastructure.reply.reply_generator.openai_reply_generator import OpenAIReplyGenerator
from talk_to_pdf.backend.app.infrastructure.retrieval.rerankers.factory_openai_reranker import OpenAILlmRerankerFactory
from talk_to_pdf.backend.app.infrastructure.retrieval.rerankers.openai_reranker import OpenaiReranker


@lru_cache(maxsize=1)
def get_open_ai_embedding_factory() -> OpenAIEmbedderFactory:
    if settings.OPENAI_API_KEY is None:
        raise RuntimeError("OPENAI_API_KEY must be set")
    return OpenAIEmbedderFactory(api_key=settings.OPENAI_API_KEY)

@lru_cache(maxsize=1)
def get_openai_reranker(conf: Annotated[RerankerConfig,Depends(get_reranker_config)]) -> OpenaiReranker:
    if settings.OPENAI_API_KEY is None:
        raise RuntimeError("OPENAI_API_KEY must be set")
    return OpenAILlmRerankerFactory(api_key=settings.OPENAI_API_KEY).create(conf)


@lru_cache(maxsize=1)
def get_open_ai_reply_generator(
        config: Annotated[ReplyGenerationConfig, Depends(get_reply_generation_config)]
)-> OpenAIReplyGenerator:
    if settings.OPENAI_API_KEY is None:
        raise RuntimeError("OPENAI_API_KEY must be set")
    return OpenAILlmReplyGeneratorFactory(api_key=settings.OPENAI_API_KEY).create(config)

@lru_cache(maxsize=1)
def get_open_ai_query_rewriter(
        config: Annotated[QueryRewriteConfig, Depends(get_query_rewrite_config)]
)-> OpenAIQueryRewriter:
    if settings.OPENAI_API_KEY is None:
        raise RuntimeError("OPENAI_API_KEY must be set")
    return OpenAILlmQueryRewriterFactory(api_key=settings.OPENAI_API_KEY).create(config)

def get_build_index_context_use_case(
        uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
        embedding_factory: Annotated[OpenAIEmbedderFactory, Depends(get_open_ai_embedding_factory)],
        query_rewriter: Annotated[OpenAIQueryRewriter, Depends(get_open_ai_query_rewriter)],
        reranker: Annotated[OpenaiReranker, Depends(get_openai_reranker)]
) -> BuildIndexContextUseCase:
    return BuildIndexContextUseCase(
        uow_factory=uow_factory,
        embedder_factory=embedding_factory,
        reranker=reranker,
        max_top_k=settings.MAX_TOP_K,
        max_top_n=settings.MAX_TOP_N,
        query_rewriter=query_rewriter,
        retrieval_merger=DeterministicRetrievalResultMerger(),
    )

def get_get_chat_messages_use_case(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)]
) -> GetChatMessagesUseCase:
    return GetChatMessagesUseCase(uow_factory=uow_factory)

def get_create_chat_message_use_case(uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)]) -> CreateChatMessageUseCase:
    return CreateChatMessageUseCase(uow_factory=uow_factory)


def get_stream_reply_use_case(
        uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
        context_builder: Annotated[ContextBuilder, Depends(get_build_index_context_use_case)],
        create_chat_message_uc: Annotated[CreateChatMessageUseCase, Depends(get_create_chat_message_use_case)],
        get_chat_messages_uc: Annotated[GetChatMessagesUseCase, Depends(get_get_chat_messages_use_case)],
        reply_generator: Annotated[OpenAIReplyGenerator, Depends(get_open_ai_reply_generator)]
) -> StreamReplyUseCase:
    return StreamReplyUseCase(
        uow_factory=uow_factory,
        ctx_builder_uc=context_builder,
        create_msg_uc=create_chat_message_uc,
        get_chat_messages_uc=get_chat_messages_uc,
        reply_generator=reply_generator,
    )


def get_create_chat_use_case(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)]
) -> CreateChatUseCase:
    return CreateChatUseCase(uow_factory=uow_factory)


def get_get_chat_use_case(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)]
) -> GetChatUseCase:
    return GetChatUseCase(uow_factory=uow_factory)


def get_list_chats_use_case(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)]
) -> ListChatsUseCase:
    return ListChatsUseCase(uow_factory=uow_factory)


def get_delete_chat_use_case(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)]
) -> DeleteChatUseCase:
    return DeleteChatUseCase(uow_factory=uow_factory)


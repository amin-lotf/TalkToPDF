from functools import lru_cache
from typing import Annotated, Callable

from fastapi import Depends

from talk_to_pdf.backend.app.application.common.interfaces import ContextBuilder, EmbedderFactory
from talk_to_pdf.backend.app.application.reply.use_cases.stream_reply import StreamReplyUseCase
from talk_to_pdf.backend.app.application.retrieval.use_cases.build_index_context import BuildIndexContextUseCase
from talk_to_pdf.backend.app.core.config import settings
from talk_to_pdf.backend.app.core.deps import get_uow, get_uow_factory
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.infrastructure.common.embedders.factory_openai_langchain import OpenAIEmbedderFactory

@lru_cache(maxsize=1)
def get_open_ai_embedding_factory() -> OpenAIEmbedderFactory:
    if settings.OPENAI_API_KEY is None:
        raise RuntimeError("OPENAI_API_KEY must be set")
    return OpenAIEmbedderFactory(api_key=settings.OPENAI_API_KEY)


def get_build_index_context_use_case(
        uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
        embedding_factory: Annotated[OpenAIEmbedderFactory, Depends(get_open_ai_embedding_factory)]
) -> BuildIndexContextUseCase:
    return BuildIndexContextUseCase(
        uow_factory=uow_factory,
        embedder_factory=embedding_factory,
        max_top_k=settings.MAX_TOP_K,
        max_top_n=settings.MAX_TOP_N,
    )



def get_stream_reply_use_case(
        uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
        context_builder: Annotated[ContextBuilder, Depends(get_build_index_context_use_case)]


) -> StreamReplyUseCase:
    return StreamReplyUseCase(uow_factory=uow_factory, ctx_builder_uc=context_builder)
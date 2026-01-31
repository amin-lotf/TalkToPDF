from dataclasses import dataclass
from langchain_openai import ChatOpenAI

from talk_to_pdf.backend.app.domain.common.value_objects import QueryRewriteConfig
from talk_to_pdf.backend.app.infrastructure.reply.query_rewriter.openai_query_rewriter import OpenAIQueryRewriter


@dataclass(frozen=True, slots=True)
class OpenAILlmQueryRewriterFactory:
    api_key: str

    def create(self, cfg: QueryRewriteConfig) -> OpenAIQueryRewriter:
        llm = ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            api_key=self.api_key,
        )
        return OpenAIQueryRewriter(llm=llm, cfg=cfg)
from dataclasses import dataclass
from langchain_openai import ChatOpenAI

from talk_to_pdf.backend.app.domain.common.value_objects import RerankerConfig
from talk_to_pdf.backend.app.infrastructure.retrieval.rerankers.openai_reranker import OpenaiReranker


@dataclass(frozen=True, slots=True)
class OpenAILlmRerankerFactory:
    api_key: str

    def create(self, cfg: RerankerConfig) -> OpenaiReranker:
        llm = ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            api_key=self.api_key,
        )
        return OpenaiReranker(llm=llm, cfg=cfg)

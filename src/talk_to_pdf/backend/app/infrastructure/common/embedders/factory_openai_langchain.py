from __future__ import annotations

from dataclasses import dataclass

from langchain_openai import OpenAIEmbeddings

from talk_to_pdf.backend.app.application.common.interfaces import AsyncEmbedder
from talk_to_pdf.backend.app.domain.common.value_objects import EmbedConfig
from talk_to_pdf.backend.app.infrastructure.common.embedders.langchain_openai_embedder import LangChainEmbedder


@dataclass(frozen=True, slots=True)
class OpenAIEmbedderFactory:
    api_key: str

    def create(self, cfg: EmbedConfig) -> AsyncEmbedder:
        embeddings = OpenAIEmbeddings(
            model=cfg.model,
            dimensions=cfg.dimensions,
            api_key=self.api_key,
        )
        return LangChainEmbedder(embeddings)

from __future__ import annotations

from typing import Protocol

from talk_to_pdf.backend.app.application.common.dto import SearchInputDTO, ContextPackDTO
from talk_to_pdf.backend.app.domain.common.value_objects import EmbedConfig


class AsyncEmbedder(Protocol):
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]: ...


class EmbedderFactory(Protocol):
    def create(self, cfg: EmbedConfig) -> AsyncEmbedder: ...


class ContextBuilder(Protocol):
    async def execute(self, dto: SearchInputDTO) -> ContextPackDTO: ...

from __future__ import annotations

from typing import List, Sequence



class LangChainEmbedder:
    """
    Thin adapter so worker uses a stable interface.
    """

    def __init__(self, lc_embeddings) -> None:
        # lc_embeddings should have: aembed_documents(texts) -> list[list[float]]
        self._lc = lc_embeddings

    async def aembed_documents(self, texts: Sequence[str]) -> List[List[float]]:
        return await self._lc.aembed_documents(list(texts))

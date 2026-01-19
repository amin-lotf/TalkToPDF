from __future__ import annotations

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from talk_to_pdf.backend.app.domain.common.value_objects import Chunk, RerankerConfig





class LangChainLlmReranker:
    def __init__(self, llm: ChatOpenAI, cfg: RerankerConfig) -> None:
        self._llm = llm
        self._cfg = cfg

        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a reranking engine. "
                    "Return JSON only. Do not add explanations.",
                ),
                (
                    "human",
                    "Query:\n{query}\n\n"
                    "Candidates:\n{candidates}\n\n"
                    'Return JSON exactly like: {"ranked_ids":["<uuid>", "..."]}\n'
                    "Rules:\n"
                    "- ranked_ids must contain ONLY ids from the candidates list\n"
                    "- Order best to worst for answering the query\n"
                    "- Include at most {top_n} ids\n"
                    "- Output JSON only",
                ),
            ]
        )
        self._parser = JsonOutputParser()

    def _clip(self, text: str) -> str:
        t = text.strip().replace("\u0000", "")
        if len(t) > self._cfg.max_chars_per_chunk:
            return t[: self._cfg.max_chars_per_chunk] + "…"
        return t

    async def rank(self, query: str, candidates: list[Chunk]) -> list[Chunk]:
        if not candidates:
            return []

        id_to_chunk: dict[str, Chunk] = {str(c.id): c for c in candidates}

        # Provide compact “cards”
        cards = []
        for c in candidates:
            cards.append(
                f"- id: {c.id}\n"
                f"  chunk_index: {c.chunk_index}\n"
                f"  text: {self._clip(c.text)}"
            )

        msgs = self._prompt.format_messages(
            query=query,
            candidates="\n".join(cards),
            top_n=self._cfg.top_n,
        )

        raw = await self._llm.ainvoke(msgs)

        # Fail-open: never break retrieval if LLM returns garbage.
        try:
            data = self._parser.parse(raw.content)
            ranked_ids = data.get("ranked_ids", [])
            ranked: list[Chunk] = [id_to_chunk[rid] for rid in ranked_ids if rid in id_to_chunk]

            # Append missing chunks in original order (stable)
            seen = set(ranked_ids)
            tail = [c for c in candidates if str(c.id) not in seen]
            return ranked + tail
        except Exception:
            return candidates

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from talk_to_pdf.backend.app.domain.common.value_objects import Chunk, RerankerConfig
from talk_to_pdf.backend.app.domain.retrieval.value_objects import RerankContext


class OpenaiReranker:
    """
    LLM reranker.

    Design choice:
    - The rerank "Query" is the *original user query* (intent anchor).
    - Sub-queries are provided only as additional context (optional),
      so reranking doesn't drift toward the rewriter's interpretation.
    """

    def __init__(self, llm: ChatOpenAI, cfg: RerankerConfig) -> None:
        self._llm = llm
        self._cfg = cfg

        # Keep prompt stable and strict: JSON-only.
        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a reranking engine for a RAG system.\n"
                    "Return JSON only. Do not add explanations.\n"
                    "Your job: reorder candidate chunks by usefulness for answering the user's query.",
                ),
                (
                    "human",
                    "User query (primary intent):\n{query}\n\n"
                    "{subqueries_block}"
                    "Candidates:\n{candidates}\n\n"
                    'Return JSON exactly like: {"ranked_ids":["<uuid>", "..."]}\n'
                    "Rules:\n"
                    "- ranked_ids must contain ONLY ids from the candidates list\n"
                    "- Order best to worst for answering the user query\n"
                    "- Include at most {top_n} ids\n"
                    "- Output JSON only",
                ),
            ]
        )
        self._parser = JsonOutputParser()


    def _format_subqueries_block(self, sub_queries: list[str] | None) -> str:
        if not sub_queries:
            return ""
        # Keep it compact; these are supporting signals only.
        lines = "\n".join([f"- {q.strip()}" for q in sub_queries if (q or "").strip()])
        if not lines:
            return ""
        return f"Supporting sub-queries (secondary signals):\n{lines}\n\n"

    def _candidate_card(
        self,
        chunk: Chunk,
        *,
        signals: dict[str, Any] | None = None,
    ) -> str:
        # Signals are optional extra info produced by your merger (matched_by, agg_score, etc.)
        sig_txt = ""
        if signals:
            # Keep signals short and JSON-ish
            # (avoid huge blobs; LLM only needs hints)
            parts: list[str] = []
            if "matched_by" in signals:
                parts.append(f"matched_by={signals['matched_by']}")
            if "agg_score" in signals:
                parts.append(f"agg_score={signals['agg_score']}")
            if parts:
                sig_txt = f"\n  signals: {', '.join(parts)}"

        return (
            f"- id: {chunk.id}\n"
            f"  chunk_index: {chunk.chunk_index}\n"
            f"  text: {chunk.text}"
            f"{sig_txt}"
        )

    async def rank(
        self,
        query: str,
        candidates: list[Chunk],
        *,
        top_n: int | None = None,
        ctx: RerankContext | None = None,
    ) -> list[Chunk]:
        """
        Backward compatible:
        - If ctx is None, behaves like the old version.
        - If ctx is provided, uses ctx.original_query as the main query and
          includes ctx.sub_queries and ctx.candidate_signals as extra context.
        """
        if not candidates:
            return []

        # Anchor on original intent
        primary_query = (ctx.original_query if ctx else query) or query
        primary_query = (primary_query or "").strip()

        id_to_chunk: dict[str, Chunk] = {str(c.id): c for c in candidates}

        signals_by_id: dict[str, dict[str, Any]] = {}
        if ctx and ctx.candidate_signals:
            signals_by_id = ctx.candidate_signals

        cards: list[str] = []
        for c in candidates:
            sig = signals_by_id.get(str(c.id))
            cards.append(self._candidate_card(c, signals=sig))

        msgs = self._prompt.format_messages(
            query=primary_query,
            subqueries_block=self._format_subqueries_block(ctx.sub_queries if ctx else None),
            candidates="\n".join(cards),
            top_n=top_n,
        )

        raw = await self._llm.ainvoke(msgs)

        # Fail-open: never break retrieval if LLM returns garbage.
        try:
            data = self._parser.parse(getattr(raw, "content", "") or "")
            ranked_ids = data.get("ranked_ids", [])

            # Keep only valid ids, preserve returned order
            ranked: list[Chunk] = []
            seen: set[str] = set()
            for rid in ranked_ids:
                sid = str(rid)
                if sid in id_to_chunk and sid not in seen:
                    ranked.append(id_to_chunk[sid])
                    seen.add(sid)

            # Append missing chunks in original order (stable)
            tail = [c for c in candidates if str(c.id) not in seen]
            return ranked + tail
        except Exception:
            return candidates

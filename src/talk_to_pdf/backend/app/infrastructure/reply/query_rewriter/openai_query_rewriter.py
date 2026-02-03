# app/infrastructure/llm/openai_query_rewriter.py
from __future__ import annotations

import json
import logging
from typing import Sequence

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage

from talk_to_pdf.backend.app.application.retrieval.value_objects import MultiQueryRewriteResult
from talk_to_pdf.backend.app.domain.common.value_objects import QueryRewriteConfig, ChatTurn
from talk_to_pdf.backend.app.infrastructure.common.token_counter import count_message_tokens

logger = logging.getLogger(__name__)

REWRITE_SYSTEM = (
    "You expand a user's question into 2-4 diverse, standalone search queries for a RAG system.\n"
    "Return only JSON with this schema: {\"queries\": [\"...\", \"...\"], \"strategy\": \"optional short note\"}.\n"
    "Guidelines:\n"
    "- Make each query specific and self-contained; resolve pronouns using conversation context.\n"
    "- Prefer diverse angles (terminology variants, constraints, sub-aspects) over minor wording tweaks.\n"
    "- Keep queries concise; no answers or explanations.\n"
    "- Ensure queries are unique, non-empty strings.\n"
)

REWRITE_HUMAN = (
    "Latest user query:\n"
    "{query}\n\n"
    "Conversation (most recent last):\n"
    "{history}\n\n"
    "Return JSON only. Avoid any extra commentary."
)




class OpenAIQueryRewriter:
    def __init__(self, *, llm: ChatOpenAI, cfg: QueryRewriteConfig) -> None:
        self._llm = llm
        self._cfg = cfg
        self.llm_model = llm.model_name

    def _clip(self, text: str, *, limit: int) -> str:
        t = (text or "").strip().replace("\u0000", "")
        if len(t) > limit:
            return t[:limit] + "\n...[clipped]"
        return t

    def _select_turns(self, history: Sequence[ChatTurn]) -> list[ChatTurn]:
        """
        Use only the most recent turns. Rewriting needs local context,
        not the whole conversation.
        """
        if not history:
            return []
        return list(history[-self._cfg.max_turns :])

    def _format_history(self, history: Sequence[ChatTurn]) -> str:
        turns = self._select_turns(history)

        # compact, readable, and role-tagged.
        lines: list[str] = []
        for t in turns:
            content = (t.content or "").strip()
            if not content:
                continue
            role = t.role.value if hasattr(t.role, "value") else str(t.role)
            # Keep each turn on a single line-ish
            content = " ".join(content.split())
            lines.append(f"{role}: {content}")

        s = "\n".join(lines)
        return self._clip(s, limit=self._cfg.max_history_chars)

    def _build_messages(self, *, query: str, history: Sequence[ChatTurn]) -> list[BaseMessage]:
        q = (query or "").strip()
        hist_txt = self._format_history(history)

        return [
            SystemMessage(content=REWRITE_SYSTEM),
            HumanMessage(
                content=REWRITE_HUMAN.format(
                    query=q,
                    history=hist_txt or "(no prior turns)",
                )
            ),
        ]

    async def rewrite(self, *, query: str, history: Sequence[ChatTurn]) -> str:
        """
        Returns the primary rewritten query string (first generated sub-query).
        Safe fallback: returns original query if parsing fails.
        """
        result = await self.rewrite_queries_with_metrics(query=query, history=history)
        return result.rewritten_query

    def _normalize_queries(self, queries: Sequence[str], *, fallback: str) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for q in queries:
            t = (q or "").strip()
            if not t:
                continue
            tnorm = " ".join(t.split())
            key = tnorm.lower()
            if key in seen:
                continue
            cleaned.append(tnorm)
            seen.add(key)

        if len(cleaned) > 4:
            cleaned = cleaned[:4]

        if not cleaned:
            fb = (fallback or "").strip()
            return [fb] if fb else []

        if len(cleaned) < 2:
            fb = (fallback or "").strip()
            if fb and fb.lower() not in seen:
                cleaned.append(fb)
            else:
                logger.warning("Query rewriter returned fewer than 2 queries; using available queries only.")

        return cleaned

    async def rewrite_queries_with_metrics(self, *, query: str, history: Sequence[ChatTurn]) -> MultiQueryRewriteResult:
        """
        Returns multiple rewritten queries with token usage metrics.
        Safe fallback: returns list containing the original query if parsing fails.
        """
        msgs = self._build_messages(query=query, history=history)

        prompt_tokens = count_message_tokens(msgs, model=self.llm_model)

        resp = await self._llm.ainvoke(msgs)
        txt = (getattr(resp, "content", "") or "").strip()

        completion_tokens = 0
        if hasattr(resp, "response_metadata"):
            usage = resp.response_metadata.get("token_usage", {})
            completion_tokens = usage.get("completion_tokens", 0)

        parsed_queries: list[str] = []
        strategy: str | None = None

        try:
            data = json.loads(txt)
            raw_queries = data.get("queries")
            if isinstance(raw_queries, str):
                raw_queries = [raw_queries]
            if isinstance(raw_queries, Sequence):
                parsed_queries = [str(q) for q in raw_queries]
            strategy_val = data.get("strategy")
            if isinstance(strategy_val, str) and strategy_val.strip():
                strategy = strategy_val.strip()
        except Exception as e:
            logger.warning("Failed to parse query rewrite response as JSON: %s", e)

        normalized = self._normalize_queries(parsed_queries, fallback=query)
        if not normalized:
            normalized = [(query or "").strip()]

        return MultiQueryRewriteResult(
            queries=normalized,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            strategy=strategy,
        )

    async def rewrite_with_metrics(self, *, query: str, history: Sequence[ChatTurn]) -> MultiQueryRewriteResult:
        """
        Backwards-compatible alias for single-query callers.
        """
        return await self.rewrite_queries_with_metrics(query=query, history=history)

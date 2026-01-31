# app/infrastructure/llm/openai_query_rewriter.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage

from talk_to_pdf.backend.app.domain.common.value_objects import QueryRewriteConfig, ChatTurn

REWRITE_SYSTEM = (
    "You are a query rewriting engine for a RAG system.\n"
    "Goal: rewrite the user's latest question into a standalone search query.\n"
    "\n"
    "Rules:\n"
    "- Return JSON only. No extra text.\n"
    "- Output schema: {\"rewritten_query\": string}\n"
    "- Keep it concise but specific.\n"
    "- Resolve pronouns (it/that/they/this) using conversation context.\n"
    "- If the question is already standalone, keep it the same.\n"
    "- Do NOT answer the question.\n"
    "- Do NOT invent details not present in the chat.\n"
)

REWRITE_HUMAN = (
    "Latest user query:\n"
    "{query}\n\n"
    "Conversation (most recent last):\n"
    "{history}\n\n"
    "Return JSON only."
)




class OpenAIQueryRewriter:
    def __init__(self, *, llm: ChatOpenAI, cfg: QueryRewriteConfig) -> None:
        self._llm = llm
        self._cfg = cfg

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
        Returns rewritten standalone query string.
        Safe fallback: returns original query if parsing fails.
        """
        msgs = self._build_messages(query=query, history=history)

        # We want a single JSON response. Use ainvoke (non-streaming).
        resp = await self._llm.ainvoke(msgs)
        txt = (getattr(resp, "content", "") or "").strip()

        # Very defensive parsing: accept only {"rewritten_query": "..."}
        # without importing extra libs if you prefer; but json is fine.
        import json

        try:
            data = json.loads(txt)
            rq = (data.get("rewritten_query") or "").strip()
            return rq if rq else (query or "").strip()
        except Exception:
            return (query or "").strip()

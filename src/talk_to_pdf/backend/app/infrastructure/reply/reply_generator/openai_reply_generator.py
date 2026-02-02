# app/infrastructure/llm/openai_answer_generator.py
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Sequence

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from talk_to_pdf.backend.app.domain.common.value_objects import ReplyGenerationConfig, ChatTurn
from talk_to_pdf.backend.app.domain.common.enums import ChatRole
from talk_to_pdf.backend.app.domain.reply.value_objects import GenerateReplyInput

DEFAULT_SYSTEM = (
    "You are a helpful assistant.\n"
    "Answer using the provided context when relevant.\n"
    "If the context does not contain the answer, say you don't know.\n"
    "Be concise and correct."
)

CONTEXT_PREAMBLE = (
    "Use the following context as your primary source.\n"
    "Context:\n"
)





class OpenAIReplyGenerator:
    def __init__(self, *, llm: ChatOpenAI, cfg: ReplyGenerationConfig) -> None:
        self._llm = llm
        self._cfg = cfg
        self.llm_model = llm.model_name

    def _clip(self, text: str) -> str:
        t = (text or "").strip().replace("\u0000", "")
        if len(t) > self._cfg.max_context_chars:
            return t[: self._cfg.max_context_chars] + "\n...[clipped]"
        return t

    def _map_turns(self, history: Sequence[ChatTurn]) -> list[BaseMessage]:
        msgs: list[BaseMessage] = []
        for t in history:
            content = (t.content or "").strip()
            if not content:
                continue
            if t.role == ChatRole.SYSTEM:
                msgs.append(SystemMessage(content=content))
            elif t.role == ChatRole.USER:
                msgs.append(HumanMessage(content=content))
            else:
                msgs.append(AIMessage(content=content))
        return msgs

    def _build_messages(self, inp: GenerateReplyInput) -> list[BaseMessage]:
        system = inp.system_prompt or DEFAULT_SYSTEM
        context = self._clip(inp.context)

        msgs: list[BaseMessage] = [
            SystemMessage(content=system),
        ]

        if context:
            # I prefer system-role context so user query stays clean
            msgs.append(SystemMessage(content=CONTEXT_PREAMBLE + context))

        msgs.extend(self._map_turns(inp.history))

        msgs.append(HumanMessage(content=inp.query.strip()))
        return msgs

    async def stream_answer(self, inp: GenerateReplyInput) -> AsyncIterator[str]:
        msgs = self._build_messages(inp)

        # LangChain streaming yields AIMessageChunk objects
        async for chunk in self._llm.astream(msgs):
            # chunk.content can be "" sometimes
            txt = getattr(chunk, "content", "") or ""
            if txt:
                yield txt

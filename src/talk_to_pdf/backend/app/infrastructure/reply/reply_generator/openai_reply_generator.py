# app/infrastructure/llm/openai_answer_generator.py
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Sequence

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from talk_to_pdf.backend.app.domain.common.value_objects import ReplyGenerationConfig, ChatTurn
from talk_to_pdf.backend.app.domain.common.enums import ChatRole
from talk_to_pdf.backend.app.domain.reply.value_objects import GenerateReplyInput
from talk_to_pdf.backend.app.infrastructure.common.token_counter import count_tokens, count_message_tokens

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


@dataclass
class PromptTokenBreakdown:
    """Breakdown of tokens in the prompt."""
    system: int
    context: int
    history: int
    question: int


@dataclass
class StreamMetrics:
    """Metrics collected during streaming."""
    prompt_breakdown: PromptTokenBreakdown
    completion_tokens: int = 0



class OpenAIReplyGenerator:
    def __init__(self, *, llm: ChatOpenAI, cfg: ReplyGenerationConfig) -> None:
        self._llm = llm
        self._cfg = cfg
        self.llm_model = llm.model_name
        self._last_metrics: StreamMetrics | None = None

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

    def _build_messages(self, inp: GenerateReplyInput) -> tuple[list[BaseMessage], PromptTokenBreakdown]:
        system = inp.system_prompt or DEFAULT_SYSTEM
        context = self._clip(inp.context)

        # Build system message
        system_msg = SystemMessage(content=system)
        msgs: list[BaseMessage] = [system_msg]

        # Count system tokens
        system_tokens = count_message_tokens([system_msg], model=self.llm_model)

        # Add context if present
        context_tokens = 0
        if context:
            context_msg = SystemMessage(content=CONTEXT_PREAMBLE + context)
            msgs.append(context_msg)
            context_tokens = count_message_tokens([context_msg], model=self.llm_model)

        # Add history
        history_msgs = self._map_turns(inp.history)
        msgs.extend(history_msgs)
        history_tokens = count_message_tokens(history_msgs, model=self.llm_model) if history_msgs else 0

        # Add user question
        question_msg = HumanMessage(content=inp.query.strip())
        question_tokens = count_message_tokens([question_msg], model=self.llm_model)

        breakdown = PromptTokenBreakdown(
            system=system_tokens,
            context=context_tokens,
            history=history_tokens,
            question=question_tokens,
        )

        return msgs, breakdown

    async def stream_answer(self, inp: GenerateReplyInput) -> AsyncIterator[str]:
        msgs, breakdown = self._build_messages(inp)

        # Initialize metrics
        completion_tokens = 0

        # LangChain streaming yields AIMessageChunk objects
        async for chunk in self._llm.astream(msgs):
            # chunk.content can be "" sometimes
            txt = getattr(chunk, "content", "") or ""
            if txt:
                # Count completion tokens (approximate per chunk)
                completion_tokens += count_tokens(txt, model=self.llm_model)
                yield txt

        # Store metrics for later retrieval
        self._last_metrics = StreamMetrics(
            prompt_breakdown=breakdown,
            completion_tokens=completion_tokens,
        )

    def get_last_metrics(self) -> StreamMetrics | None:
        """Get metrics from the last stream_answer call."""
        return self._last_metrics

    def clear_metrics(self) -> None:
        """Clear stored metrics."""
        self._last_metrics = None

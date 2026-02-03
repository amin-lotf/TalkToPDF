"""Metrics value objects for tracking token usage and latency."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TokenMetrics:
    """Token usage metrics for prompt components."""
    system: int = 0
    history: int = 0
    rewritten_question: int = 0
    context: int = 0
    question: int = 0

    @property
    def total(self) -> int:
        """Total prompt tokens."""
        return self.system + self.history + self.rewritten_question + self.context + self.question


@dataclass(frozen=True, slots=True)
class LatencyMetrics:
    """Latency metrics for different processing stages (in seconds)."""
    query_rewriting: float | None = None
    retrieval: float | None = None
    reply_generation: float | None = None

    @property
    def total(self) -> float:
        """Total latency across all stages."""
        return sum(
            v for v in [self.query_rewriting, self.retrieval, self.reply_generation]
            if v is not None
        )


@dataclass(frozen=True, slots=True)
class ReplyMetrics:
    """
    Complete metrics for a reply generation request.

    Tracks:
    - Token usage breakdown for prompt components
    - Completion tokens
    - Total tokens
    - Latency for each processing stage
    """
    prompt_tokens: TokenMetrics
    completion_tokens: int = 0
    latency: LatencyMetrics = field(default_factory=LatencyMetrics)

    @property
    def total_tokens(self) -> int:
        """Total tokens (prompt + completion)."""
        return self.prompt_tokens.total + self.completion_tokens

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "tokens": {
                "prompt": {
                    "system": self.prompt_tokens.system,
                    "history": self.prompt_tokens.history,
                    "rewritten_question": self.prompt_tokens.rewritten_question,
                    "context": self.prompt_tokens.context,
                    "question": self.prompt_tokens.question,
                    "total": self.prompt_tokens.total,
                },
                "completion": self.completion_tokens,
                "total": self.total_tokens,
            },
            "latency": {
                "query_rewriting": self.latency.query_rewriting,
                "retrieval": self.latency.retrieval,
                "reply_generation": self.latency.reply_generation,
                "total": self.latency.total,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReplyMetrics:
        """Create from dictionary."""
        if not isinstance(data, dict):
            # Defensive: fallback to empty metrics when bad payload types are encountered.
            data = {}

        tokens_data = data.get("tokens", {}) if isinstance(data.get("tokens"), dict) else {}
        prompt_data = tokens_data.get("prompt", {}) if isinstance(tokens_data.get("prompt"), dict) else {}
        latency_data = data.get("latency", {}) if isinstance(data.get("latency"), dict) else {}

        return cls(
            prompt_tokens=TokenMetrics(
                system=prompt_data.get("system", 0),
                history=prompt_data.get("history", 0),
                rewritten_question=prompt_data.get("rewritten_question", 0),
                context=prompt_data.get("context", 0),
                question=prompt_data.get("question", 0),
            ),
            completion_tokens=tokens_data.get("completion", 0),
            latency=LatencyMetrics(
                query_rewriting=latency_data.get("query_rewriting"),
                retrieval=latency_data.get("retrieval"),
                reply_generation=latency_data.get("reply_generation"),
            ),
        )

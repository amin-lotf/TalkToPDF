"""Token counting utility using tiktoken for accurate model-specific token counts."""
from __future__ import annotations

from typing import Sequence, Any
from functools import lru_cache
import json

import tiktoken
from langchain_core.messages import BaseMessage


@lru_cache(maxsize=10)
def _get_encoding(model: str) -> tiktoken.Encoding:
    """Get tiktoken encoding for a model, with caching."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Prefer newer fallback when available; else cl100k_base.
        # (o200k_base is used by many newer models; cl100k_base is common for older chat models.)
        try:
            return tiktoken.get_encoding("o200k_base")
        except Exception:
            return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in a text string using the model's tokenizer.

    Args:
        text: Text to count tokens for
        model: Model name (e.g., "gpt-4", "gpt-3.5-turbo")

    Returns:
        Number of tokens
    """
    if not text:
        return 0

    encoding = _get_encoding(model)
    return len(encoding.encode(text))


def _stringify_content(content: Any) -> str:
    """
    LangChain message.content can be:
      - str
      - list[dict|str|...], e.g. [{"type":"text","text":"..."}, ...]
    Convert to a stable, tokenizable string representation.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                # Common LC format: {"type":"text","text":"..."}
                if "text" in block and isinstance(block["text"], str):
                    parts.append(block["text"])
                else:
                    parts.append(json.dumps(block, ensure_ascii=False, sort_keys=True))
            else:
                parts.append(str(block))
        return "\n".join(p for p in parts if p)
    # Fallback: preserve something rather than lose content
    return str(content)


def _stringify_additional_kwargs(message: BaseMessage) -> str:
    """
    additional_kwargs may include tool/function call payloads.
    We include them because they can materially affect prompt tokens.
    """
    ak = getattr(message, "additional_kwargs", None) or {}
    if not ak:
        return ""

    # Make it stable and avoid non-serializable objects causing crashes.
    try:
        return json.dumps(ak, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(ak)


def count_message_tokens(messages: Sequence[BaseMessage], model: str = "gpt-4") -> int:
    """
    Count tokens in a sequence of LangChain messages.

    Notes:
    - This is an *estimate* of chat formatting overhead (tokens_per_message, priming, etc.).
    - Content + additional_kwargs tokenization is real (tiktoken), but overhead varies by model/provider.
    - For exact numbers, use API response usage.prompt_tokens / completion_tokens.

    Args:
        messages: Sequence of LangChain BaseMessage objects
        model: Model name

    Returns:
        Total number of tokens including formatting (estimated overhead).
    """
    if not messages:
        return 0

    encoding = _get_encoding(model)

    # Heuristic overhead for chat-style formatting.
    # (These constants are not universal; keep them as best-effort guardrails.)
    tokens_per_message = 3
    tokens_per_name = 1
    reply_priming = 3

    num_tokens = 0

    for message in messages:
        num_tokens += tokens_per_message

        # Count content tokens (handles str or block-list content)
        content_text = _stringify_content(getattr(message, "content", None))
        if content_text:
            num_tokens += len(encoding.encode(content_text))

        # Count "name" tokens if present
        name = getattr(message, "name", None)
        if name:
            num_tokens += tokens_per_name

        # Include tool/function payloads if present
        ak_text = _stringify_additional_kwargs(message)
        if ak_text:
            num_tokens += len(encoding.encode(ak_text))

    # Add priming tokens for assistant reply
    num_tokens += reply_priming

    return num_tokens

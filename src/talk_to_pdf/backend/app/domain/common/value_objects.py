from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence, Any
from uuid import UUID

from talk_to_pdf.backend.app.domain.common.enums import ChatRole


@dataclass(frozen=True, slots=True)
class Vector:
    values: tuple[float, ...]
    dim: int

    @classmethod
    def from_list(cls, values: Sequence[float]) -> "Vector":
        values = tuple(float(v) for v in values)
        return cls(values=values, dim=len(values))


@dataclass(frozen=True, slots=True)
class Chunk:
    id: UUID
    index_id: UUID
    chunk_index: int
    text: str
    meta: dict[str, Any] | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EmbedConfig:
    provider: str
    model: str
    batch_size: int
    dimensions: int | None

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "batch_size": int(self.batch_size),
            "dimensions": (int(self.dimensions) if self.dimensions is not None else None),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmbedConfig":
        # strict parsing: reject unknown keys
        allowed = {"provider", "model", "batch_size", "dimensions"}
        unknown = set(d.keys()) - allowed
        if unknown:
            raise ValueError(f"Unknown keys in embed_config: {sorted(unknown)}")

        return cls(
            provider=str(d["provider"]),
            model=str(d["model"]),
            batch_size=int(d["batch_size"]),
            dimensions=(int(d["dimensions"]) if d.get("dimensions") is not None else None),
        )

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def signature(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RerankerConfig:
    provider: str           # "openai", "noop", "cross_encoder"
    model: str              # "gpt-4o-mini", "bge-reranker"
    temperature: float = 0.0

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": float(self.temperature),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RerankerConfig":
        allowed = {
            "provider",
            "model",
            "temperature",
        }
        unknown = set(d.keys()) - allowed
        if unknown:
            raise ValueError(f"Unknown keys in reranker_config: {sorted(unknown)}")

        return cls(
            provider=str(d["provider"]),
            model=str(d["model"]),
            temperature=float(d.get("temperature", 0.0)),
        )

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def signature(self) -> str:
        """
        Optional.
        Useful for debugging / observability, NOT for indexing.
        """
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ReplyGenerationConfig:
    provider: str
    model: str
    temperature: float = 0.2
    max_output_tokens: int | None = None
    max_context_chars: int = 20_000  # safety clip

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": float(self.temperature),
            "max_output_tokens": int(self.max_output_tokens) if self.max_output_tokens is not None else None,
            "max_context_chars": int(self.max_context_chars),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReplyGenerationConfig":
        allowed = {
            "provider",
            "model",
            "temperature",
            "max_output_tokens",
            "max_context_chars",
        }
        unknown = set(d.keys()) - allowed
        if unknown:
            raise ValueError(f"Unknown keys in reranker_config: {sorted(unknown)}")

        return cls(
            provider=str(d["provider"]),
            model=str(d["model"]),
            temperature=float(d.get("temperature", 0.0)),
            max_output_tokens=int(d.get("max_output_tokens")) if d.get("max_output_tokens") is not None else None,
            max_context_chars=int(d.get("max_context_chars", 20_000))
        )

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def signature(self) -> str:
        """
        Optional.
        Useful for debugging / observability, NOT for indexing.
        """
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class QueryRewriteConfig:
    # keep only the last N turns to avoid noise
    provider: str
    model: str
    temperature: float = 0.2
    max_turns: int = 6
    # hard cap on history text to avoid bloating prompts
    max_history_chars: int = 6000

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_turns": self.max_turns,
            "max_history_chars": self.max_history_chars,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QueryRewriteConfig":
        allowed = {
            "provider",
            "model",
            "temperature",
            "max_turns",
            "max_history_chars",
        }
        unknown = set(d.keys()) - allowed
        if unknown:
            raise ValueError(f"Unknown keys in reranker_config: {sorted(unknown)}")

        return cls(
            max_turns=int(d.get("max_turns", 6)),
            max_history_chars=int(d.get("max_history_chars", 6000)),
        )

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def signature(self) -> str:
        """
        Optional.
        Useful for debugging / observability, NOT for indexing.
        """
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ChatTurn:
    role: ChatRole
    content: str

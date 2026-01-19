import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence, Any
from uuid import UUID


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
    top_n: int
    temperature: float = 0.0
    max_chars_per_chunk: int = 900

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "top_n": int(self.top_n),
            "temperature": float(self.temperature),
            "max_chars_per_chunk": int(self.max_chars_per_chunk),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RerankerConfig":
        allowed = {
            "provider",
            "model",
            "top_n",
            "temperature",
            "max_chars_per_chunk",
        }
        unknown = set(d.keys()) - allowed
        if unknown:
            raise ValueError(f"Unknown keys in reranker_config: {sorted(unknown)}")

        return cls(
            provider=str(d["provider"]),
            model=str(d["model"]),
            top_n=int(d["top_n"]),
            temperature=float(d.get("temperature", 0.0)),
            max_chars_per_chunk=int(d.get("max_chars_per_chunk", 900)),
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
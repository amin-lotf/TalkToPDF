import hashlib
import json
from dataclasses import dataclass
from typing import Any, Sequence
from uuid import UUID


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
class ChunkDraft:
    chunk_index: int
    text: str
    meta: dict[str, Any] | None = None



@dataclass(frozen=True, slots=True)
class Vector:
    values: tuple[float, ...]
    dim: int

    @classmethod
    def from_list(cls, values: Sequence[float]) -> "Vector":
        values = tuple(float(v) for v in values)
        return cls(values=values, dim=len(values))


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingDraft:
    """
    Domain draft for persisting an embedding.
    """
    chunk_id: UUID
    chunk_index: int
    vector: Vector
    meta: dict[str, Any] | None = None  # optional per-embedding metadata


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingRef:
    """
    What you need to identify an embedding row without exposing DB model.
    """
    id: UUID
    chunk_id: UUID
    chunk_index: int
    embed_signature: str


@dataclass(frozen=True, slots=True)
class ChunkMatch:
    """
    Retrieval result: which chunk matched and with what score/distance.
    """
    chunk_id: UUID
    chunk_index: int
    score: float  # interpretation depends on metric (similarity or negative distance)
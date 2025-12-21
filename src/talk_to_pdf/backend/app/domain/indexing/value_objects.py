import hashlib
import json
from dataclasses import dataclass


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
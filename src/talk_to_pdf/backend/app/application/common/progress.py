# app/application/common/progress.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    name: str                 # "embed_start", "vector_search_done", ...
    payload: dict[str, Any]   # small JSON-serializable dict


class ProgressSink(Protocol):
    async def emit(self, event: ProgressEvent) -> None: ...

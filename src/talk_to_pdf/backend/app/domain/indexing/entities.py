from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from ..common.value_objects import EmbedConfig
from .enums import IndexStatus
from ..common import utcnow


@dataclass(frozen=True, slots=True)
class DocumentIndex:
    """
    Domain representation of an indexing run for a document.
    Entity because it has identity (id) and lifecycle (status/progress).
    """
    project_id: UUID
    document_id: UUID
    storage_path: str
    chunker_version: str
    embed_config: EmbedConfig
    message: Optional[str] = None
    error: Optional[str] = None
    progress: int = 0
    status: IndexStatus = IndexStatus.PENDING
    cancel_requested: bool = False
    updated_at: datetime = field(default_factory=utcnow)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not (0 <= self.progress <= 100):
            raise ValueError("progress must be between 0 and 100")

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal

    @property
    def is_active(self) -> bool:
        return self.status.is_active

    @property
    def embed_signature(self) -> str:
        return self.embed_config.signature()

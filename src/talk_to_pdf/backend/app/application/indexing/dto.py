from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional
from uuid import UUID
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus


@dataclass(frozen=True, slots=True)
class IndexStatusDTO:
    project_id: UUID
    document_id: UUID
    index_id: UUID
    storage_path: str
    status: IndexStatus
    progress: int  # 0..100
    message: Optional[str] = None
    error: Optional[str] = None
    cancel_requested: bool = False
    updated_at: Optional[datetime] = None
    meta: Optional[Mapping[str, Any]] = None



@dataclass(frozen=True, slots=True)
class StartIndexingInputDTO:
    owner_id: UUID
    project_id: UUID
    document_id: UUID



@dataclass(frozen=True, slots=True)
class GetIndexStatusByIdInputDTO:
    owner_id: UUID
    index_id: UUID


@dataclass(frozen=True, slots=True)
class GetLatestIndexStatusInputDTO:
    owner_id: UUID
    project_id: UUID


@dataclass(frozen=True, slots=True)
class CancelIndexingInputDTO:
    owner_id: UUID
    index_id: UUID

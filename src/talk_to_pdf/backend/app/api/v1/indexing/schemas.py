from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus


class IndexStatusResponse(BaseModel):
    project_id: UUID
    document_id: UUID
    index_id: UUID
    storage_path: str

    status: IndexStatus
    progress: int

    message: Optional[str] = None
    error: Optional[str] = None
    cancel_requested: bool = False
    updated_at: Optional[datetime] = None
    meta: Optional[Mapping[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

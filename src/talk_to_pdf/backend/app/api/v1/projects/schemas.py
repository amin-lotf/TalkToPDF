from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class CreateProjectRequest(BaseModel):
    """
    JSON request body. Note: file upload will NOT be here.
    We'll take the file from `UploadFile = File(...)` in the endpoint.
    """
    name: str = Field(min_length=2, max_length=100)


class ProjectDocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    download_url: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime
    main_document: ProjectDocumentResponse

    model_config = ConfigDict(from_attributes=True)


class RenameProjectRequest(BaseModel):
    new_name: str = Field(min_length=2, max_length=100)


class ListProjectsResponse(BaseModel):
    items: list[ProjectResponse]

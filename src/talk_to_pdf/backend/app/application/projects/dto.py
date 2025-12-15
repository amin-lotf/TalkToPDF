from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID




@dataclass(frozen=True)
class CreateProjectInputDTO:
    owner_id: UUID
    name: str
    file_bytes: bytes
    filename: str
    content_type: str

@dataclass(frozen=True)
class GetProjectInputDTO:
    owner_id: UUID
    project_id: UUID


@dataclass(frozen=True)
class RenameProjectInputDTO:
    owner_id: UUID
    project_id: UUID
    new_name: str


@dataclass(frozen=True)
class DeleteProjectInputDTO:
    owner_id: UUID
    project_id: UUID


@dataclass(frozen=True)
class ListProjectsInputDTO:
    owner_id: UUID


# ---------- OUTPUT DTOs ----------
@dataclass(frozen=True)
class ProjectDocumentDTO:
    id: UUID
    original_filename: str
    storage_path: str     # or a URL if you want to expose that
    content_type: str
    size_bytes: int
    uploaded_at: datetime

@dataclass(frozen=True)
class ProjectDTO:
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime
    primary_document: ProjectDocumentDTO

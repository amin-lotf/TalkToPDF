# talk_to_pdf/backend/app/domain/projects/entities.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from .value_objects import ProjectName
from ..common import utcnow


@dataclass
class ProjectDocument:
    project_id: UUID
    original_filename: str
    storage_path: str  # or a FileLocation VO if you want to be fancy
    content_type: str  # "application/pdf"
    size_bytes: int
    id: UUID = field(default_factory=uuid4)
    uploaded_at: datetime = field(default_factory=utcnow)


@dataclass
class Project:
    name: ProjectName
    owner_id: UUID
    primary_document: Optional[ProjectDocument] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


    def rename(self, new_name: ProjectName) -> None:
       self.name = new_name

    def attach_main_document(self, document: ProjectDocument) -> Project:
        return Project(
            id=self.id,
            name=self.name,
            owner_id=self.owner_id,
            primary_document=document,
            created_at=self.created_at
        )



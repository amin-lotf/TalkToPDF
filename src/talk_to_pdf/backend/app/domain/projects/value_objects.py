# talk_to_pdf/backend/app/domain/projects/value_objects.py
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4





@dataclass(frozen=True)
class ProjectName:
    value: str

    def __post_init__(self) -> None:
        name = self.value.strip()

        if not name:
            raise ValueError("Project name cannot be empty.")

        if len(name) > 200:
            raise ValueError("Project name must be at most 200 characters.")

        # normalize stored value
        object.__setattr__(self, "value", name)



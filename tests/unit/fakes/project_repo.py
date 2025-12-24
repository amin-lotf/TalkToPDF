from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from typing import Optional
from uuid import UUID

from talk_to_pdf.backend.app.domain.projects.entities import Project
from talk_to_pdf.backend.app.domain.projects.value_objects import ProjectName


class FakeProjectRepository:
    """
    In-memory fake for ProjectRepository.

    Design goals:
    - deterministic
    - no implicit side effects
    - mirrors domain semantics (rename, attach document via entity methods)
    """

    def __init__(self) -> None:
        # canonical storage by id
        self._projects: dict[UUID, Project] = {}

    # ---------- Commands ----------

    async def add(self, project: Project) -> Project:
        # store a defensive copy to avoid external mutation
        stored = deepcopy(project)
        self._projects[stored.id] = stored
        return deepcopy(stored)

    async def delete(self, project_id: UUID) -> None:
        self._projects.pop(project_id, None)

    async def rename(self, *, project: Project) -> Project:
        """
        Assumes the Project entity already has the new name applied
        via project.rename(new_name).
        """
        if project.id not in self._projects:
            raise KeyError(f"Project {project.id} not found")

        # replace stored entity with the updated one
        self._projects[project.id] = deepcopy(project)
        return deepcopy(project)

    # ---------- Queries ----------

    async def get_by_id(self, *, project_id: UUID) -> Optional[Project]:
        project = self._projects.get(project_id)
        return deepcopy(project) if project else None

    async def get_by_owner_and_id(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
    ) -> Optional[Project]:
        project = self._projects.get(project_id)
        if project and project.owner_id == owner_id:
            return deepcopy(project)
        return None

    async def list_by_owner(self, owner_id: UUID) -> Sequence[Project]:
        return [
            deepcopy(p)
            for p in self._projects.values()
            if p.owner_id == owner_id
        ]

    # ---------- Test helpers (optional but useful) ----------

    def _add_raw(self, project: Project) -> None:
        """
        Insert without copying.
        Useful for setting up fixtures quickly.
        """
        self._projects[project.id] = project

    def _all(self) -> list[Project]:
        """
        Inspect internal state in assertions if needed.
        """
        return list(self._projects.values())

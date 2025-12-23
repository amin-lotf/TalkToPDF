from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import delete as sa_delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.domain.projects import Project
from talk_to_pdf.backend.app.infrastructure.projects.mappers import (
    create_project_domain_from_models,
    project_domain_to_model,
    project_document_domain_to_model,
)
from talk_to_pdf.backend.app.infrastructure.db.models.project import ProjectModel, ProjectDocumentModel


class SqlAlchemyProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, project: Project) -> Project:
        if project.primary_document is None:
            raise ValueError("Project.primary_document must be set before calling add()")

        pm = project_domain_to_model(project)
        dm = project_document_domain_to_model(project.primary_document)

        # Wire both ends of the cycle using Python-generated UUIDs
        dm.project_id = pm.id
        pm.primary_document_id = dm.id

        self._session.add_all([pm, dm])
        await self._session.flush()

        await self._session.refresh(pm)
        await self._session.refresh(dm)
        return create_project_domain_from_models(pm, dm)

    async def get_by_id(self,  project_id: UUID) -> Optional[Project]:
        stmt = (
            select(ProjectModel, ProjectDocumentModel)
            .join(ProjectDocumentModel, ProjectDocumentModel.id == ProjectModel.primary_document_id)
            .where(ProjectModel.id == project_id)
        )
        res = await self._session.execute(stmt)
        row = res.one_or_none()
        if row is None:
            return None
        pm, dm = row
        return create_project_domain_from_models(pm, dm)

    async def get_by_owner_and_id(self, owner_id: UUID, project_id: UUID) -> Optional[Project]:
        stmt = (
            select(ProjectModel, ProjectDocumentModel)
            .join(ProjectDocumentModel, ProjectDocumentModel.id == ProjectModel.primary_document_id)
            .where(ProjectModel.owner_id == owner_id)
            .where(ProjectModel.id == project_id)
        )
        res = await self._session.execute(stmt)
        row = res.one_or_none()
        if row is None:
            return None
        pm, dm = row
        return create_project_domain_from_models(pm, dm)

    async def list_by_owner(self, owner_id: UUID) -> Sequence[Project]:
        stmt = (
            select(ProjectModel, ProjectDocumentModel)
            .join(ProjectDocumentModel, ProjectDocumentModel.id == ProjectModel.primary_document_id)
            .where(ProjectModel.owner_id == owner_id)
            .order_by(ProjectModel.created_at.desc())
        )
        res = await self._session.execute(stmt)
        return [create_project_domain_from_models(pm, dm) for pm, dm in res.all()]

    async def delete(self, project_id: UUID) -> None:
        await self._session.execute(
            sa_delete(ProjectModel).where(ProjectModel.id == project_id)
        )
        await self._session.flush()

    async def rename(self,  project: Project) -> Project:
        """
        Persist a renamed Project (updates only projects.name).
        Returns the fully-hydrated domain Project (with primary_document).
        """
        # Update name in DB
        await self._session.execute(
            update(ProjectModel)
            .where(ProjectModel.id == project.id)
            .values(name=project.name.value)  # ProjectName -> str
        )
        await self._session.flush()

        # Re-load (joined) so we return Project + ProjectDocument consistently
        stmt = (
            select(ProjectModel, ProjectDocumentModel)
            .join(ProjectDocumentModel, ProjectDocumentModel.id == ProjectModel.primary_document_id)
            .where(ProjectModel.id == project.id)
        )
        res = await self._session.execute(stmt)
        row = res.one_or_none()
        if row is None:
            # If you prefer domain exceptions, raise ProjectNotFound here
            raise ValueError(f"Project {project.id} not found")
        pm, dm = row
        return create_project_domain_from_models(pm, dm)

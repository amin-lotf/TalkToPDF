from uuid import UUID
from fastapi import UploadFile

from talk_to_pdf.backend.app.api.v1.projects.schemas import ListProjectsResponse, ProjectResponse
from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO, GetProjectInputDTO, \
    ListProjectsInputDTO, ProjectDTO


def get_create_project_input_dto(
        user_id: UUID,
        project_name:str,
        file: UploadFile,
        file_bytes: bytes
) -> CreateProjectInputDTO:
    return CreateProjectInputDTO(
        owner_id=user_id,
        name=project_name,
        file_bytes=file_bytes,
        filename=file.filename or "uploaded.pdf",
        content_type=file.content_type or "application/octet-stream",
    )

def get_get_project_input_dto(
    user_id: UUID,
        project_id:UUID
)->GetProjectInputDTO:
    return GetProjectInputDTO(
        owner_id=user_id,
        project_id=project_id
    )


def get_list_projects_input_dto(
        user_id: UUID,
)->ListProjectsInputDTO:
    return ListProjectsInputDTO(owner_id=user_id)


def projects_dts_to_schema(projects_dto:list[ProjectDTO])->ListProjectsResponse:
    items = [ProjectResponse.model_validate(p) for p in projects_dto]
    return ListProjectsResponse(items=items)
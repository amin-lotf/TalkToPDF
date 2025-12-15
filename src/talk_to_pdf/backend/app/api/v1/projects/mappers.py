from uuid import UUID

from fastapi import UploadFile

from talk_to_pdf.backend.app.api.v1.projects.schemas import CreateProjectRequest
from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO


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

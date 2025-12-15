from typing import Annotated

from fastapi import APIRouter, UploadFile, File, Depends, Form

from talk_to_pdf.backend.app.api.v1.projects.deps import get_create_project_use_case
from talk_to_pdf.backend.app.api.v1.projects.mappers import get_create_project_input_dto
from talk_to_pdf.backend.app.api.v1.projects.schemas import ProjectResponse, CreateProjectRequest
from talk_to_pdf.backend.app.api.v1.users.deps import get_logged_in_user
from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO, ProjectDTO
from talk_to_pdf.backend.app.application.projects.use_cases import CreateProjectUseCase
from talk_to_pdf.backend.app.application.users import CurrentUserDTO

router = APIRouter(prefix="/projects", tags=["projects"])

logged_in_user_dep=Annotated[CurrentUserDTO, Depends(get_logged_in_user)]
create_project_dep=Annotated[CreateProjectUseCase,Depends(get_create_project_use_case)]
@router.post("/create", response_model=ProjectResponse)
async def create_project(
    user: logged_in_user_dep,
    name: Annotated[str, Form(min_length=1, max_length=100)] ,                       # user typed name
    file: UploadFile = File(...),                # user uploaded file
    use_case=Depends(get_create_project_use_case),
):
    file_bytes = await file.read()
    dto:CreateProjectInputDTO = get_create_project_input_dto(user.id, name, file, file_bytes)
    project_dto: ProjectDTO = await use_case.execute(dto)
    return ProjectResponse.model_validate(project_dto)
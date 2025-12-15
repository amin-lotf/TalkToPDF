from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, Depends, Form, status

from talk_to_pdf.backend.app.api.v1.projects.deps import get_create_project_use_case, get_get_project_use_case, \
    get_list_user_projects_use_case, get_delete_project_use_case, get_rename_project_use_case
from talk_to_pdf.backend.app.api.v1.projects.mappers import get_create_project_input_dto, get_get_project_input_dto, \
    get_list_projects_input_dto, projects_dts_to_schema, get_delete_project_input_dto, get_rename_project_input_dto
from talk_to_pdf.backend.app.api.v1.projects.schemas import ProjectResponse, ListProjectsResponse, RenameProjectRequest
from talk_to_pdf.backend.app.api.v1.users.deps import get_logged_in_user
from talk_to_pdf.backend.app.application.projects.use_cases import CreateProjectUseCase, ListUserProjectsUseCase, \
    DeleteProjectUseCase, RenameProjectUseCase
from talk_to_pdf.backend.app.application.projects.use_cases.get_project import GetProjectUseCase
from talk_to_pdf.backend.app.application.users import CurrentUserDTO

router = APIRouter(prefix="/projects", tags=["projects"])

logged_in_user_dep = Annotated[CurrentUserDTO, Depends(get_logged_in_user)]
create_project_dep = Annotated[CreateProjectUseCase, Depends(get_create_project_use_case)]
get_project_dep = Annotated[GetProjectUseCase, Depends(get_get_project_use_case)]
get_list_projects_dep = Annotated[ListUserProjectsUseCase, Depends(get_list_user_projects_use_case)]
get_delete_project_dep = Annotated[DeleteProjectUseCase,Depends(get_delete_project_use_case)]
get_rename_project_dep = Annotated[RenameProjectUseCase,Depends(get_rename_project_use_case)]


@router.post("/create", response_model=ProjectResponse)
async def create_project(
        user: logged_in_user_dep,
        use_case: create_project_dep,
        name: Annotated[str, Form(min_length=1, max_length=100)],  # user typed name
        file: UploadFile = File(...),  # user uploaded file
):
    file_bytes = await file.read()
    dto = get_create_project_input_dto(user.id, name, file, file_bytes)
    project_dto = await use_case.execute(dto)
    return ProjectResponse.model_validate(project_dto)



@router.get("", response_model=ListProjectsResponse)
async def get_projects(
        user: logged_in_user_dep,
        use_case:get_list_projects_dep,
):
    request_dto=get_list_projects_input_dto(user.id)
    projects_dto = await use_case.execute(request_dto)
    return projects_dts_to_schema(projects_dto)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
        user: logged_in_user_dep,
        use_case:get_project_dep,
        project_id:UUID
):
    request_dto = get_get_project_input_dto(user.id,project_id)
    project_dto = await use_case.execute(request_dto)
    return ProjectResponse.model_validate(project_dto)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    user: logged_in_user_dep,
    use_case: get_delete_project_dep,
    project_id: str,
) -> None:
    dto = get_delete_project_input_dto(user.id, UUID(project_id))
    await use_case.execute(dto)
    return None

@router.patch("/{project_id}/rename", response_model=ProjectResponse)
async def rename_project(
    user: logged_in_user_dep,
    use_case: get_rename_project_dep,
    project_id: UUID,
    body: RenameProjectRequest,
) -> ProjectResponse:
    dto = get_rename_project_input_dto(user.id, project_id, body.new_name)
    project_dto = await use_case.execute(dto)
    return ProjectResponse.model_validate(project_dto)
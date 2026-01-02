from fastapi import FastAPI,Request, status
from fastapi.responses import JSONResponse

from talk_to_pdf.backend.app.domain.files.errors import FailedToSaveFile
from talk_to_pdf.backend.app.domain.indexing.errors import FailedToStartIndexing, IndexNotFound, NoIndexesForProject
from talk_to_pdf.backend.app.domain.projects.errors import ProjectNotFound, FailedToCreateProject
from talk_to_pdf.backend.app.domain.users import InvalidCredentialsError, InactiveUserError, UserNotFoundError, \
    RegistrationError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials(_: Request, __: InvalidCredentialsError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid credentials"},
        )

    @app.exception_handler(InactiveUserError)
    async def inactive_user(_: Request, __: InactiveUserError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "User is inactive"},
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found(_: Request, __: UserNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "User not found"},
        )

    @app.exception_handler(RegistrationError)
    async def registration_error(_: Request, exc: RegistrationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc) or "Registration failed"},
        )

    @app.exception_handler(ProjectNotFound)
    async def project_not_found(_: Request, exc: ProjectNotFound):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(FailedToSaveFile)
    async def failed_to_save_file(_: Request, exc: FailedToSaveFile):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc) or "Failed to save file"},
        )

    @app.exception_handler(FailedToCreateProject)
    async def failed_to_create_project(_: Request, exc: FailedToCreateProject):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )

    @app.exception_handler(FailedToStartIndexing)
    async def failed_to_start_indexing(_: Request, exc: FailedToStartIndexing):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )

    @app.exception_handler(IndexNotFound)
    async def index_not_found(_: Request, exc: IndexNotFound):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(NoIndexesForProject)
    async def index_for_project_not_found(_: Request, exc: NoIndexesForProject):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )


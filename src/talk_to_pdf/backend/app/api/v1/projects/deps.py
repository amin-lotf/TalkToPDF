from typing import Annotated

from fastapi import Depends

from talk_to_pdf.backend.app.application.projects.use_cases import CreateProjectUseCase
from talk_to_pdf.backend.app.core import get_uow
from talk_to_pdf.backend.app.core.deps import get_file_storage
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.infrastructure.db.uow import UnitOfWork


async def get_create_project_use_case(
        uow: Annotated[UnitOfWork, Depends(get_uow)],
        storage: Annotated[FileStorage, Depends(get_file_storage)]
) -> CreateProjectUseCase:
    return CreateProjectUseCase(uow,storage)
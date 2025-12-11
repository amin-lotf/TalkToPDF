from typing import Annotated

from fastapi.params import Depends
from talk_to_pdf.backend.app.application.users.use_cases import RegisterUserUseCase
from talk_to_pdf.backend.app.core import BcryptPasswordHasher
from talk_to_pdf.backend.app.core import get_uow
from talk_to_pdf.backend.app.infrastructure.db import UnitOfWork


def get_password_hasher()->BcryptPasswordHasher:
    return BcryptPasswordHasher()

async def get_register_user_use_case(
    uow: Annotated[UnitOfWork,Depends(get_uow)],
    hasher: Annotated[BcryptPasswordHasher,Depends(get_password_hasher)]
):
    return RegisterUserUseCase(uow.user_repo,hasher)
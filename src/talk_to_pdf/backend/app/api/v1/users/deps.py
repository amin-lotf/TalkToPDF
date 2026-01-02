import uuid
from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, status
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from talk_to_pdf.backend.app.application.users import CurrentUserDTO
from talk_to_pdf.backend.app.application.users.use_cases import RegisterUserUseCase, LoginUserUseCase
from talk_to_pdf.backend.app.application.users.use_cases.get_current_user import GetCurrentUserUseCase
from talk_to_pdf.backend.app.core.security import BcryptPasswordHasher, decode_access_token
from talk_to_pdf.backend.app.core.deps import get_uow
from talk_to_pdf.backend.app.domain.users import UserNotFoundError
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error= not settings.SKIP_AUTH
)


def get_password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


async def get_register_user_use_case(
        uow: Annotated[UnitOfWork, Depends(get_uow)],
        hasher: Annotated[BcryptPasswordHasher, Depends(get_password_hasher)]
) -> RegisterUserUseCase:
    return RegisterUserUseCase(uow, hasher)


async def get_login_user_use_case(
        uow: Annotated[UnitOfWork, Depends(get_uow)],
        hasher: Annotated[BcryptPasswordHasher, Depends(get_password_hasher)]
) -> LoginUserUseCase:
    return LoginUserUseCase(uow, hasher)


async def get_current_user_use_case(
        uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> GetCurrentUserUseCase:
    return GetCurrentUserUseCase(uow)

DEV_USER = CurrentUserDTO(id=UUID('79376ad0-f4ea-42a7-ac46-5bbbbbe45f46'), email="dev@example.com", name="devmod", is_active=True)

async def ensure_dev_user_exists(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> None:
    if not settings.SKIP_AUTH:
        return

    async with uow:
        # Adjust repo method names to yours:
        existing = await uow.users.get_by_id(DEV_USER.id)
        if existing is None:
            # Create domain user however your domain expects
            user = await uow.users.create(  # or uow.users.add(...)
                id=DEV_USER.id,
                email=DEV_USER.email,
                name=DEV_USER.name,
                is_active=True,
                # password_hash=None etc, depending on schema
            )

async def get_jwt_payload(token: Annotated[str|None, Depends(oauth2_scheme)]) -> dict:
    if settings.SKIP_AUTH:
        return {"sub": str(DEV_USER.id)}
    try:
        payload = decode_access_token(token)
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
        )


async def get_logged_in_user(
        payload: Annotated[dict , Depends(get_jwt_payload)],
        use_case: Annotated[GetCurrentUserUseCase, Depends(get_current_user_use_case)],
) -> CurrentUserDTO:
    if settings.SKIP_AUTH:
        return DEV_USER
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    try:
        user_id = UUID(sub)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
        )

    try:
        user = await use_case.execute(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user



from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from talk_to_pdf.backend.app.api.v1.users import UserResponse, RegisterUserRequest, TokenResponse, LoginRequest
from talk_to_pdf.backend.app.api.v1.users.deps import get_register_user_use_case, get_login_user_use_case, \
    get_logged_in_user
from talk_to_pdf.backend.app.api.v1.users.mappers import request_to_input_dto, output_dto_to_response, \
    login_request_to_input_dto
from talk_to_pdf.backend.app.application.users import RegisterUserOutput, CurrentUserDTO
from talk_to_pdf.backend.app.application.users.use_cases import RegisterUserUseCase, LoginUserUseCase
from talk_to_pdf.backend.app.core.security import create_access_token
from talk_to_pdf.backend.app.domain.users import RegistrationError
from talk_to_pdf.backend.app.domain.users.erorrs import InvalidCredentialsError, InactiveUserError

router = APIRouter(prefix="/auth", tags=["auth"])

register_user_dep=Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)]
login_user_dep=Annotated[LoginUserUseCase, Depends(get_login_user_use_case)]
logged_in_user_dep=Annotated[CurrentUserDTO, Depends(get_logged_in_user)]

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    body: RegisterUserRequest,
    use_case: register_user_dep,
) -> UserResponse:
    try:
        input_dto=request_to_input_dto(body)
        result: RegisterUserOutput = await use_case.execute(input_dto)
    except RegistrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    output_response=output_dto_to_response(result)
    return output_response

@router.post(
    path="/token",
    response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    use_case: login_user_dep
) -> TokenResponse:
    input_dto = login_request_to_input_dto(payload)

    try:
        result = await use_case.execute(input_dto)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = create_access_token(subject=str(result.id))
    return TokenResponse(access_token=access_token)

@router.get("/me")
async def get_me(current_user:logged_in_user_dep):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "is_active": current_user.is_active,
    }
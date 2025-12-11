from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from talk_to_pdf.backend.app.api.v1.users import UserResponse, RegisterUserRequest
from talk_to_pdf.backend.app.api.v1.users.mappers import request_to_input_dto, output_dto_to_response
from talk_to_pdf.backend.app.application.users import RegisterUserOutput
from talk_to_pdf.backend.app.application.users.use_cases import RegisterUserUseCase
from talk_to_pdf.backend.app.domain.users import RegistrationError
from talk_to_pdf.backend.app.infrastructure.users import get_register_user_use_case

router = APIRouter(prefix="/auth", tags=["auth"])



@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    body: RegisterUserRequest,
    use_case: Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)],
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
from __future__ import annotations
from pydantic import EmailStr, TypeAdapter
from talk_to_pdf.backend.app.api.v1.users import RegisterUserRequest, UserResponse, LoginRequest
from talk_to_pdf.backend.app.application.users import RegisterUserInput, RegisterUserOutput, LoginUserInputDTO


def request_to_input_dto(user_request:RegisterUserRequest)->RegisterUserInput:
    return RegisterUserInput(
        email=str(user_request.email), 
        name=user_request.name,
        password=user_request.password
    )

def output_dto_to_response(user:RegisterUserOutput)->UserResponse:
    email = TypeAdapter(EmailStr).validate_python(user.email)
    return UserResponse(
        id=user.id,
        email=email,
        name=user.name,
        created_at=user.created_at,
    )

def login_request_to_input_dto(data: LoginRequest) -> LoginUserInputDTO:
    return LoginUserInputDTO(
        email=str(data.email),
        password=data.password,
    )
from talk_to_pdf.backend.app.application.users import RegisterUserOutput, RegisterUserInput, LoginUserOutputDTO, \
    CurrentUserDTO
from talk_to_pdf.backend.app.domain.users import User


def register_domain_to_output_dto(user:User)->RegisterUserOutput:
    return RegisterUserOutput(
        id=user.id,
        email=str(user.email),
        name=user.name,
        created_at=user.created_at
    )

def register_input_dto_to_domain(data:RegisterUserInput)->User:
    from talk_to_pdf.backend.app.domain.users import UserEmail
    return User(
        id=None,
        email=UserEmail(data.email),
        name=data.name,
        hashed_password=None,
        is_active=True,
        created_at=None
    )

def login_domain_to_output_dto(user:User)->LoginUserOutputDTO:
    return LoginUserOutputDTO(
        id=user.id,
        email=str(user.email),
        is_active=user.is_active
    )

def current_domain_to_output_dto(user:User)->CurrentUserDTO:
    return CurrentUserDTO(
        id=user.id,
        email=str(user.email),
        name=user.name,
        is_active=user.is_active
    )
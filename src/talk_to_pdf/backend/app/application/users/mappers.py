from talk_to_pdf.backend.app.application.users import RegisterUserOutput, RegisterUserInput
from talk_to_pdf.backend.app.domain.users import User


def domain_to_output_dto(user:User)->RegisterUserOutput:
    return RegisterUserOutput(
        id=user.id,
        email=str(user.email),
        name=user.name,
        created_at=user.created_at
    )

def input_dto_to_domain(data:RegisterUserInput)->User:
    from talk_to_pdf.backend.app.domain.users import UserEmail
    return User(
        id=None,
        email=UserEmail(data.email),
        name=data.name,
        hashed_password=None,
        is_active=True,
        created_at=None
    )
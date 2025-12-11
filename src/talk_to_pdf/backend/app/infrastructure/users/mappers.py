from uuid import UUID

from talk_to_pdf.backend.app.domain.users import User, UserEmail
from talk_to_pdf.backend.app.infrastructure.users.models import UserModel


def model_to_domain(model: UserModel) -> User:
    return User(
        id=UUID(model.id),
        email=UserEmail(model.email),
        name=model.name,
        hashed_password=model.hashed_password,
        is_active=model.is_active,
        created_at=model.created_at,
    )

def domain_to_model(user: User) -> UserModel:
    return UserModel(
        email=user.email.value,
        name=user.name,
        hashed_password=user.hashed_password,
        is_active=user.is_active,
    )
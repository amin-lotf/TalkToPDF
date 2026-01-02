# app/core/security.py
from datetime import timedelta, datetime, timezone
from typing import Union, Any
from jose import jwt, JWTError
from passlib.context import CryptContext

from talk_to_pdf.backend.app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptPasswordHasher:
    def hash(self, raw_password: str) -> str:
        return pwd_context.hash(raw_password)

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(raw_password, hashed_password)


ACCESS_TOKEN_EXPIRE_MINUTES = 60  # tweak if you want


def create_access_token(
    subject: Union[str, int],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token with a `sub` claim.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    to_encode: dict[str, Any] = {"sub": str(subject), "iat": now, "exp": expire}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Invalid or expired token")
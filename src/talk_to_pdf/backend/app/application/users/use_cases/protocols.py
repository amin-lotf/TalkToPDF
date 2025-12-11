from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, raw_password: str) -> str:
        ...
    def verify(self, plain: str, hashed: str) -> bool:  # pragma: no cover - interface
        ...
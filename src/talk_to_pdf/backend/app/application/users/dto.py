from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class RegisterUserInput:
    email: str
    name: str
    password: str


@dataclass
class RegisterUserOutput:
    id: UUID
    email: str
    name: str
    created_at: datetime

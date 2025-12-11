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


@dataclass
class LoginUserInputDTO:
    email: str
    password: str


@dataclass
class LoginUserOutputDTO:
    id: UUID
    email: str
    is_active: bool


@dataclass
class CurrentUserDTO:
    id: UUID
    email: str
    name: str
    is_active: bool
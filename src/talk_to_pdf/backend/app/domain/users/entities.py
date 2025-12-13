from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .value_objects import UserEmail
from ..common import utcnow


@dataclass(slots=True, frozen=True)
class User:
    email: UserEmail
    name: str
    hashed_password: str | None

    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=utcnow)

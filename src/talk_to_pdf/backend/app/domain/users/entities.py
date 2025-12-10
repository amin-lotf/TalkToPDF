from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from .value_objects import UserEmail


@dataclass
class User:
    id: Optional[UUID]
    email: UserEmail
    name: str
    hashed_password: Optional[str]
    is_active: bool = True
    created_at: Optional[datetime] = None

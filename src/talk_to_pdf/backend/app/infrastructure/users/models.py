# app/infrastructure/auth/models.py
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # if using Postgres
from sqlalchemy.orm import Mapped, mapped_column
from talk_to_pdf.backend.app.infrastructure.db import Base


class UserModel(Base):
    __tablename__ = "users"

    # If using Postgres, you can use PG_UUID; for SQLite you can fallback to String
    # Here I'll keep String-based UUID for portability
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

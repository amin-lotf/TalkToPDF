from __future__ import annotations

from enum import StrEnum


class IndexStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in {IndexStatus.READY, IndexStatus.FAILED, IndexStatus.CANCELLED}

    @property
    def is_active(self) -> bool:
        return self in {IndexStatus.PENDING, IndexStatus.RUNNING}

    @classmethod
    def active(cls) -> tuple["IndexStatus", ...]:
        return cls.PENDING, cls.RUNNING
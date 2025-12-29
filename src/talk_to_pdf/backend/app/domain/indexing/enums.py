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


class IndexStep(StrEnum):
    QUEUED = "QUEUED"
    EXTRACTING = "EXTRACTING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    STORING = "STORING"
    FINALIZING = "FINALIZING"


STEP_PROGRESS: dict[IndexStep, int] = {
    IndexStep.QUEUED: 0,
    IndexStep.EXTRACTING: 5,
    IndexStep.CHUNKING: 20,
    IndexStep.EMBEDDING: 60,
    IndexStep.STORING: 85,
    IndexStep.FINALIZING: 95
}


class VectorMetric(StrEnum):
    COSINE = "cosine"
    L2 = "l2"
    INNER_PRODUCT = "ip"
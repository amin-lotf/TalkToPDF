from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChunkMatch:
    """
    Retrieval result: which chunk matched and with what score/distance.
    """
    chunk_id: UUID
    chunk_index: int
    score: float  # interpretation depends on metric (similarity or negative distance)




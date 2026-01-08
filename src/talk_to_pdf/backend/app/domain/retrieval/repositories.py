from typing import Protocol
from uuid import UUID

from talk_to_pdf.backend.app.domain.common.enums import VectorMetric
from talk_to_pdf.backend.app.domain.common.value_objects import Vector
from talk_to_pdf.backend.app.domain.retrieval.value_objects import ChunkMatch


class ChunkSearchRepository(Protocol):
    async def similarity_search(
        self,
        *,
        query: Vector,
        top_k: int,
        embed_signature: str,
        index_id: UUID,
        metric: VectorMetric = VectorMetric.COSINE,
    ) -> list[ChunkMatch]: ...
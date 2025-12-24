from __future__ import annotations

from uuid import UUID
from talk_to_pdf.backend.app.infrastructure.indexing.worker_factory import build_worker


async def run_indexing(*, index_id: UUID) -> None:
    worker = build_worker()
    await worker.run(index_id=index_id)

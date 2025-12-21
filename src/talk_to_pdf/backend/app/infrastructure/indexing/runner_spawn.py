from __future__ import annotations

import asyncio
from multiprocessing import get_context
from typing import Dict
from uuid import UUID

import anyio

from talk_to_pdf.backend.app.infrastructure.indexing.worker import run_indexing

_mp = get_context("spawn")
_active: Dict[UUID, "_mp.Process"] = {}


def _worker_entry(index_id: str) -> None:
    # Child process entrypoint (sync)
    asyncio.run(run_indexing(index_id=UUID(index_id)))


class SpawnProcessIndexingRunner:
    async def enqueue(self, *, index_id: UUID) -> None:
        # Avoid double-start
        p = _active.get(index_id)
        if p and p.is_alive():
            return

        proc = _mp.Process(
            target=_worker_entry,
            args=(str(index_id),),
            daemon=False,
        )
        proc.start()
        _active[index_id] = proc

    async def stop(self, *, index_id: UUID) -> None:
        p = _active.get(index_id)

        def _graceful_stop(proc):
            if proc and proc.is_alive():
                proc.join(timeout=10)
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=10)
                    if proc.is_alive():
                        try:
                            proc.kill()
                        except Exception:
                            pass

        if p:
            await anyio.to_thread.run_sync(_graceful_stop, p)
            _active.pop(index_id, None)

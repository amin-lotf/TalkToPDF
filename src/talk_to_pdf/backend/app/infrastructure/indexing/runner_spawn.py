from __future__ import annotations

import asyncio
from multiprocessing import get_context
from typing import Dict
from uuid import UUID

import anyio

from talk_to_pdf.backend.app.infrastructure.indexing.worker import run_indexing

_mp = get_context("spawn")
_active: Dict[UUID, "_mp.Process"] = {}
_lock = anyio.Lock()


def _worker_entry(index_id: str) -> None:
    asyncio.run(run_indexing(index_id=UUID(index_id)))


def _prune_dead() -> None:
    dead = [idx for idx, p in _active.items() if not p.is_alive()]
    for idx in dead:
        _active.pop(idx, None)


class SpawnProcessIndexingRunner:
    async def enqueue(self, *, index_id: UUID) -> None:
        async with _lock:
            _prune_dead()

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

    async def is_running(self, *, index_id: UUID) -> bool:
        async with _lock:
            p = _active.get(index_id)
            return bool(p and p.is_alive())

    async def stop(self, *, index_id: UUID) -> None:
        async with _lock:
            p = _active.get(index_id)

        def _graceful_stop(proc):
            if not proc or not proc.is_alive():
                return

            proc.join(timeout=10)
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=10)

            # last resort
            if proc.is_alive():
                try:
                    proc.kill()
                    proc.join(timeout=10)
                except Exception:
                    pass

        if p:
            await anyio.to_thread.run_sync(_graceful_stop, p)

        async with _lock:
            _active.pop(index_id, None)
            _prune_dead()

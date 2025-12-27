from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncContextManager, Awaitable, Callable, Optional
from uuid import UUID

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.application.indexing.interfaces import Chunker, EmbedderFactory, TextExtractor
from talk_to_pdf.backend.app.application.indexing.progress import report
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus, IndexStep
from talk_to_pdf.backend.app.domain.indexing.value_objects import ChunkDraft, EmbedConfig, Vector


def _batched(items: list[str], batch_size: int) -> list[list[str]]:
    if batch_size <= 0:
        batch_size = 64
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


@dataclass(frozen=True, slots=True)
class WorkerDeps:
    extractor: TextExtractor
    chunker: Chunker
    embedder_factory: EmbedderFactory
    file_storage: FileStorage
    session_factory: Callable[[], AsyncContextManager[AsyncSession]]
    uow_factory: Callable[[AsyncSession], UnitOfWork]


UowFn = Callable[[UnitOfWork], Awaitable[Any]]


class IndexingWorkerService:
    def __init__(self, deps: WorkerDeps) -> None:
        self.deps = deps

    async def _with_uow(self, fn: UowFn) -> Any:
        async with self.deps.session_factory() as session:
            uow = self.deps.uow_factory(session)
            async with uow:
                return await fn(uow)

    async def _cancel(self, *, uow: UnitOfWork, index_id: UUID) -> None:
        await uow.index_repo.delete_index_artifacts(index_id=index_id)
        await report(
            uow=uow,
            index_id=index_id,
            status=IndexStatus.CANCELLED,
            message="Cancelled",
        )

    async def load_index_metadata(
        self, *, uow: UnitOfWork, index_id: UUID
    ) -> Optional[tuple[UUID, UUID, EmbedConfig, str]]:
        """
        Returns (project_id, document_id, embed_cfg, storage_path) or None if index not found/cancelled.
        NOTE: If idx.embed_config is stored as dict/JSON, convert it to EmbedConfig here.
        This code intentionally does NOT assume any specific conversion API exists.
        """
        idx = await uow.index_repo.get_by_id(index_id=index_id)
        if not idx:
            return None

        if idx.cancel_requested:
            await self._cancel(uow=uow, index_id=index_id)
            return None

        embed_cfg = idx.embed_config  # may already be EmbedConfig, or may be dict/JSON depending on your repo/model
        storage_path = idx.storage_path

        return idx.project_id, idx.document_id, embed_cfg, storage_path

    async def extract_text(self, storage_path: str) -> str:
        try:
            pdf_bytes = await self.deps.file_storage.read_bytes(storage_path=storage_path)
        except Exception as e:
            raise RuntimeError("Failed to read PDF file") from e

        try:
            # NOTE: extractor.extract is assumed sync here (as in your code).
            # If it becomes slow, you may want to offload to a thread.
            text = await anyio.to_thread.run_sync(lambda: self.deps.extractor.extract(content=pdf_bytes))
            return text
        except Exception as e:
            raise RuntimeError("Failed to extract text") from e

    async def create_and_store_chunks(self, *, index_id: UUID, text: str) -> Optional[list[ChunkDraft]]:
        chunks = self.deps.chunker.chunk(text)

        async def _persist(uow: UnitOfWork) -> Optional[list[ChunkDraft]]:
            if await uow.index_repo.is_cancel_requested(index_id=index_id):
                await self._cancel(uow=uow, index_id=index_id)
                return None

            await uow.chunk_repo.bulk_create(index_id=index_id, chunks=chunks)
            return chunks

        return await self._with_uow(_persist)

    async def mark_failed(self, *, uow: UnitOfWork, index_id: UUID, error: str) -> None:
        await report(
            uow=uow,
            index_id=index_id,
            status=IndexStatus.FAILED,
            message="Failed to process document",
            error=error,
        )

    async def run(self, *, index_id: UUID) -> None:
        # 1) Load metadata (short DB transaction)
        loaded = await self._with_uow(lambda uow: self.load_index_metadata(uow=uow, index_id=index_id))
        if not loaded:
            return

        _, _, embed_cfg, storage_path = loaded

        # 2) Report: extracting (short DB transaction)
        await self._with_uow(
            lambda uow: report(
                uow=uow,
                index_id=index_id,
                status=IndexStatus.RUNNING,
                step=IndexStep.EXTRACTING,
                message="Extracting text",
            )
        )

        # 3) Extract (no DB session held)
        try:
            text = await self.extract_text(storage_path)
        except Exception as e:
            await self._with_uow(lambda uow: self.mark_failed(uow=uow, index_id=index_id, error=str(e)))
            return

        # 4) Report: chunking (short DB transaction)
        await self._with_uow(
            lambda uow: report(
                uow=uow,
                index_id=index_id,
                status=IndexStatus.RUNNING,
                step=IndexStep.CHUNKING,
                message=f"Chunking the text with {len(text)} characters",
            )
        )

        # 5) Chunk + persist (chunking itself is pure; persistence uses short DB transaction)
        chunks = await self.create_and_store_chunks(index_id=index_id, text=text)
        if not chunks:
            return

        # Build texts for embedding
        texts = [c.text for c in chunks]

        # 6) Embed (batched)
        embedder = self.deps.embedder_factory.create(embed_cfg)

        vectors: list[Vector] = []
        try:
            batches = _batched(texts, embed_cfg.batch_size)
            total = len(texts)
            done = 0
            start_p, end_p = 35, 85

            for bi, batch in enumerate(batches):
                # 6a) DB: cancel check + progress update (short transaction)
                async def _progress(uow: UnitOfWork) -> bool:
                    if await uow.index_repo.is_cancel_requested(index_id=index_id):
                        await self._cancel(uow=uow, index_id=index_id)
                        return False

                    pct = start_p + int((done / max(1, total)) * (end_p - start_p))
                    await uow.index_repo.update_progress(
                        index_id=index_id,
                        status=IndexStatus.RUNNING,
                        progress=pct,
                        message=f"Embedding batch {bi + 1}/{len(batches)}",
                        meta={
                            "embedder": embed_cfg.model,
                            "batch_size": embed_cfg.batch_size,
                            "done": done,
                            "total": total,
                        },
                    )
                    return True

                should_continue = await self._with_uow(_progress)
                if not should_continue:
                    return

                # 6b) Network: embed outside any DB session
                raw = await embedder.aembed_documents(batch)
                vectors.extend(Vector.from_list(v) for v in raw)
                done += len(batch)

        except Exception as e:
            async def _fail(uow: UnitOfWork) -> None:
                await uow.index_repo.update_progress(
                    index_id=index_id,
                    status=IndexStatus.FAILED,
                    progress=35,
                    message="Embedding failed",
                    error=str(e),
                )

            await self._with_uow(_fail)
            return

        # 7) Finalize (no vector storage yet)
        async def _finalize(uow: UnitOfWork) -> None:
            if await uow.index_repo.is_cancel_requested(index_id=index_id):
                await self._cancel(uow=uow, index_id=index_id)
                return

            await uow.index_repo.update_progress(
                index_id=index_id,
                status=IndexStatus.READY,
                progress=100,
                message="Index ready",
                meta={"chunks": len(chunks), "embedder": embed_cfg.model},
            )

        await self._with_uow(_finalize)

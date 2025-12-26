from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import AsyncContextManager, Callable
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from talk_to_pdf.backend.app.application.indexing.interfaces import EmbedderFactory, Chunker, TextExtractor
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig, Vector


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


class IndexingWorkerService:
    def __init__(self, deps: WorkerDeps) -> None:
        self.deps = deps



    async def _cancel(self, *, uow: UnitOfWork, index_id: UUID) -> None:
        await uow.index_repo.delete_index_artifacts(index_id=index_id)
        await uow.index_repo.update_progress(
            index_id=index_id,
            status=IndexStatus.CANCELLED,
            progress=0,
            message="Cancelled",
        )

    async def _load_index_metadata(self, *, index_id: UUID) -> tuple[UUID, UUID, EmbedConfig, str] | None:
        """
        Returns (project_id, document_id, embed_cfg,storage_path) or None if index not found.
        embed_cfg is parsed from dict using EmbedConfig.from_dict.
        """
        async with self.deps.session_factory() as session:
            uow = self.deps.uow_factory(session)
            async with uow:
                idx = await uow.index_repo.get_by_id(index_id=index_id)
                if not idx:
                    return None

                if idx.cancel_requested:
                    await self._cancel(uow=uow, index_id=index_id)
                    return None

                # idx.embed_config is JSON/dict in DB; parse VO
                embed_cfg =idx.embed_config

                await uow.index_repo.update_progress(
                    index_id=index_id,
                    status=IndexStatus.RUNNING,
                    progress=5,
                    message="Loading document",
                    meta={"embedder": embed_cfg.model},
                )

                return idx.project_id, idx.document_id, embed_cfg,idx.storage_path

    async def run(self, *, index_id: UUID) -> None:
        loaded = await self._load_index_metadata(index_id=index_id)
        if not loaded:
            return
        project_id, document_id, embed_cfg,storage_path = loaded
        # 2) Extract (pure)
        try:
            pdf_bytes = await self.deps.file_storage.read_bytes(storage_path=storage_path)
            text = self.deps.extractor.extract(content=pdf_bytes)
        except Exception as e:
            async with self.deps.session_factory() as session:
                uow = self.deps.uow_factory(session)
                async with uow:
                    await uow.index_repo.update_progress(
                        index_id=index_id,
                        status=IndexStatus.FAILED,
                        progress=0,
                        message="Failed to extract text",
                        error=str(e),
                    )
            return
        lines = text.splitlines()
        print("\n".join(lines[:10]))
        # 3) Chunk (pure)
        # chunks = self.deps.chunker.chunk(text)
        # texts = [c.text for c in chunks]
        #
        # # 3b) Persist chunks
        # async with self.deps.session_factory() as session:
        #     uow = self.deps.uow_factory(session)
        #     async with uow:
        #         if await uow.index_repo.is_cancel_requested(index_id=index_id):
        #             await self._cancel(uow=uow, index_id=index_id)
        #             return
        #
        #         await uow.index_repo.update_progress(
        #             index_id=index_id,
        #             status=IndexStatus.RUNNING,
        #             progress=20,
        #             message=f"Chunking ({len(chunks)} chunks)",
        #         )
        #
        #         await uow.chunk_repo.bulk_create(index_id=index_id, chunks=chunks)
        #
        # # 4) Embed (batched)
        # embedder = self.deps.embedder_factory.create(embed_cfg)
        #
        # vectors: list[Vector] = []
        # try:
        #     batches = _batched(texts, embed_cfg.batch_size)
        #     total = len(texts)
        #     done = 0
        #     start_p, end_p = 35, 85
        #
        #     for bi, batch in enumerate(batches):
        #         # 4a) DB: cancel check + progress update (short session)
        #         async with self.deps.session_factory() as session:
        #             uow = self.deps.uow_factory(session)
        #             async with uow:
        #                 if await uow.index_repo.is_cancel_requested(index_id=index_id):
        #                     await self._cancel(uow=uow, index_id=index_id)
        #                     return
        #
        #                 pct = start_p + int((done / max(1, total)) * (end_p - start_p))
        #                 await uow.index_repo.update_progress(
        #                     index_id=index_id,
        #                     status=IndexStatus.RUNNING,
        #                     progress=pct,
        #                     message=f"Embedding batch {bi + 1}/{len(batches)}",
        #                     meta={
        #                         "embedder": embed_cfg.model,
        #                         "batch_size": embed_cfg.batch_size,
        #                         "done": done,
        #                         "total": total,
        #                     },
        #                 )
        #                 # no manual commit here; uow.__aexit__ will commit
        #
        #         # 4b) Network: do embedding OUTSIDE any DB session (no connection held)
        #         raw = await embedder.aembed_documents(batch)
        #         vectors.extend(Vector.from_list(v) for v in raw)
        #         done += len(batch)
        #
        # except Exception as e:
        #     async with self.deps.session_factory() as session:
        #         uow = self.deps.uow_factory(session)
        #         async with uow:
        #             await uow.index_repo.update_progress(
        #                 index_id=index_id,
        #                 status=IndexStatus.FAILED,
        #                 progress=35,
        #                 message="Embedding failed",
        #                 error=str(e),
        #             )
        #     return
        #
        # # 5) Finalize (no vector storage yet)
        # async with self.deps.session_factory() as session:
        #     uow = self.deps.uow_factory(session)
        #     async with uow:
        #         if await uow.index_repo.is_cancel_requested(index_id=index_id):
        #             await self._cancel(uow=uow, index_id=index_id)
        #             return
        #
        #         await uow.index_repo.update_progress(
        #             index_id=index_id,
        #             status=IndexStatus.READY,
        #             progress=100,
        #             message="Index ready",
        #             meta={"chunks": len(chunks), "embedder": embed_cfg.model},
        #         )

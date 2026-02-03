from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncContextManager, Awaitable, Callable, Optional
from uuid import UUID

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from talk_to_pdf.backend.app.application.indexing.interfaces import BlockChunker, BlockExtractor, PdfToXmlConverter
from talk_to_pdf.backend.app.application.common.interfaces import EmbedderFactory
from talk_to_pdf.backend.app.application.indexing.indexing_progress import report
from talk_to_pdf.backend.app.domain.common.uow import UnitOfWork
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus, IndexStep, STEP_PROGRESS
from talk_to_pdf.backend.app.domain.indexing.value_objects import Block, ChunkDraft
from talk_to_pdf.backend.app.domain.common.value_objects import Vector, EmbedConfig
from talk_to_pdf.backend.app.infrastructure.indexing.mappers import create_chunk_embedding_drafts


def _batched(items: list[Any], batch_size: int) -> list[list[Any]]:
    if batch_size <= 0:
        batch_size = 64
    return [items[i: i + batch_size] for i in range(0, len(items), batch_size)]


@dataclass(frozen=True, slots=True)
class WorkerDeps:
    pdf_to_xml_converter: PdfToXmlConverter
    block_extractor: BlockExtractor
    block_chunker: BlockChunker
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

    async def convert_pdf_to_xml(self, storage_path: str) -> str:
        try:
            pdf_bytes = await self.deps.file_storage.read_bytes(storage_path=storage_path)
        except Exception as e:
            raise RuntimeError("Failed to read PDF file") from e

        try:
            return await anyio.to_thread.run_sync(
                lambda: self.deps.pdf_to_xml_converter.convert(content=pdf_bytes)
            )
        except Exception as e:
            raise RuntimeError("Failed to convert PDF to TEI XML") from e

    async def extract_blocks_from_xml(self, xml: str) -> list[Block]:
        try:
            return await anyio.to_thread.run_sync(lambda: self.deps.block_extractor.extract(xml=xml))
        except Exception as e:
            raise RuntimeError("Failed to parse TEI XML into blocks") from e

    async def create_and_store_chunks(self, *, index_id: UUID, blocks: list[Block]) -> Optional[list[ChunkDraft]]:
        try:
            chunks = await anyio.to_thread.run_sync(lambda: self.deps.block_chunker.chunk(blocks=blocks))
        except Exception as e:
            raise RuntimeError("Failed to chunk blocks") from e

        async def _persist(uow: UnitOfWork) -> Optional[list[ChunkDraft]]:
            if await uow.index_repo.is_cancel_requested(index_id=index_id):
                await self._cancel(uow=uow, index_id=index_id)
                return None

            await uow.chunk_repo.bulk_create(index_id=index_id, chunks=chunks)
            return chunks

        return await self._with_uow(_persist)

    async def embed_chunks(self,index_id: UUID, chunks: list[ChunkDraft],embed_cfg:EmbedConfig) -> list[Vector] | None:
        embedder = self.deps.embedder_factory.create(embed_cfg)
        texts= [c.text for c in chunks]
        vectors: list[Vector] = []
        try:
            batches = list(_batched(texts, embed_cfg.batch_size))
            total = len(texts)
            done = 0
            start_p = STEP_PROGRESS[IndexStep.EMBEDDING]
            end_p = STEP_PROGRESS[IndexStep.STORING]
            for bi, batch in enumerate(batches):
                # 6a) DB: cancel check + progress update (short transaction)
                async def _progress(uow: UnitOfWork) -> bool:
                    if await uow.index_repo.is_cancel_requested(index_id=index_id):
                        await self._cancel(uow=uow, index_id=index_id)
                        return False

                    pct = start_p + int((done / max(1, total)) * (end_p - start_p))
                    await report(
                        uow=uow,
                        index_id=index_id,
                        status=IndexStatus.RUNNING,
                        step=IndexStep.EMBEDDING,
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
                    return None

                # 6b) Network: embed outside any DB session
                raw = await embedder.aembed_documents(batch)
                vectors.extend(Vector.from_list(v) for v in raw)
                done += len(batch)
            return vectors
        except Exception as e:
            await self._with_uow(
                lambda uow: self.mark_failed(uow=uow, index_id=index_id, error=str(e))
            )
            return None

    async def store_embeds(
            self,
            *,
            index_id: UUID,
            chunks: list[ChunkDraft],
            embeds: list[Vector],
            embed_cfg: EmbedConfig,
    ) -> None:
        """
        Persist embeddings for chunks of this index.
        Assumes:
          - `chunks` are in chunk_index order (or at least their chunk_index matches DB ordering)
          - `embeds` are produced in the same order as `chunks` texts were embedded
        """
        if len(chunks) != len(embeds):
            raise ValueError(f"chunks/embeds length mismatch: {len(chunks)} vs {len(embeds)}")

        embed_signature = embed_cfg.signature()

        async def _persist(uow: UnitOfWork) -> None:
            # Cancel check
            if await uow.index_repo.is_cancel_requested(index_id=index_id):
                await self._cancel(uow=uow, index_id=index_id)
                return

            # 1) Get chunk_ids ordered by chunk_index (repo guarantees order)
            chunk_ids = await uow.chunk_repo.list_chunk_ids(index_id=index_id)
            if len(chunk_ids) != len(chunks):
                raise RuntimeError(
                    f"DB chunk count mismatch for index {index_id}: "
                    f"{len(chunk_ids)} in DB vs {len(chunks)} in memory"
                )

            # 2) Build drafts with (chunk_id, chunk_index, vector)
            # We trust both lists are aligned by chunk_index order.
            drafts= create_chunk_embedding_drafts(embeds=embeds, chunks=chunks,chunk_ids=chunk_ids,meta=None)
            # 3) Upsert
            await uow.chunk_embedding_repo.bulk_upsert(
                index_id=index_id,
                embed_signature=embed_signature,
                embeddings=drafts,
            )

            # 4) Mark ready
            await report(
                uow=uow,
                index_id=index_id,
                status=IndexStatus.READY,
                step=IndexStep.STORING,
                progress=100,
                message="Index ready",
                meta={
                    "chunks": len(chunks),
                    "embedder": embed_cfg.model,
                    "embed_signature": embed_signature,
                },
            )


        await self._with_uow(_persist)

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
                message="Converting PDF to TEI XML",
            )
        )

        # 3) Convert PDF -> TEI XML (no DB session held)
        try:
            xml = await self.convert_pdf_to_xml(storage_path)
        except Exception as e:
            await self._with_uow(lambda uow: self.mark_failed(uow=uow, index_id=index_id, error=str(e)))
            return

        # 4) Extract blocks (no DB session held)
        try:
            blocks = await self.extract_blocks_from_xml(xml)
        except Exception as e:
            await self._with_uow(lambda uow: self.mark_failed(uow=uow, index_id=index_id, error=str(e)))
            return

        # 5) Report: chunking (short DB transaction)
        await self._with_uow(
            lambda uow: report(
                uow=uow,
                index_id=index_id,
                status=IndexStatus.RUNNING,
                step=IndexStep.CHUNKING,
                message=f"Chunking {len(blocks)} blocks",
            )
        )

        # 6) Chunk + persist (chunking itself is pure; persistence uses short DB transaction)
        try:
            chunks = await self.create_and_store_chunks(index_id=index_id, blocks=blocks)
        except Exception as e:
            await self._with_uow(lambda uow: self.mark_failed(uow=uow, index_id=index_id, error=str(e)))
            return
        if not chunks:
            return
        # 7) Embed (batched)
        embeds = await self.embed_chunks(index_id=index_id, chunks=chunks,embed_cfg=embed_cfg)
        if embeds is None:
            return

        await self.store_embeds(index_id=index_id, chunks=chunks, embeds=embeds, embed_cfg=embed_cfg)

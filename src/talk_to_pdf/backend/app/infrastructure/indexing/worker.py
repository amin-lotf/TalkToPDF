from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
from uuid import UUID
from langchain_openai import OpenAIEmbeddings
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig
from talk_to_pdf.backend.app.infrastructure.indexing.embedders.langchain_openai_embedder import LangChainEmbedder
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.infrastructure.db.session import SessionLocal
from talk_to_pdf.backend.app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from talk_to_pdf.backend.app.infrastructure.indexing.models import ChunkModel
from talk_to_pdf.backend.app.core import settings


# ---------- Text extraction (minimal) ----------
def extract_text_from_pdf(pdf_path: Path) -> str:
    from pypdf import PdfReader  # local import to keep worker import lightweight

    reader = PdfReader(str(pdf_path))
    parts: List[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


# ---------- Chunking (minimal, deterministic) ----------
def chunk_text(text: str, *, max_chars: int = 1200, overlap: int = 150) -> List[Tuple[str, dict]]:
    """
    Very simple character-based chunking (good enough for v1).
    Returns list of (chunk_text, meta).
    """
    text = text.strip()
    if not text:
        return []

    chunks: List[Tuple[str, dict]] = []
    start = 0
    n = len(text)

    chunk_idx = 0
    while start < n:
        end = min(start + max_chars, n)
        chunk = text[start:end].strip()
        if chunk:
            meta = {"char_start": start, "char_end": end, "chunk_index": chunk_idx}
            chunks.append((chunk, meta))
            chunk_idx += 1

        if end >= n:
            break
        start = max(0, end - overlap)

    return chunks


# ---------- Helper: update index progress ----------
async def _set_progress(
    *,
    uow: SqlAlchemyUnitOfWork,
    index_id: UUID,
    status: IndexStatus,
    progress: int,
    message: str | None = None,
    error: str | None = None,
    meta: dict | None = None,
) -> None:
    await uow.index_repo.update_progress(
        index_id=index_id,
        status=status,
        progress=progress,
        message=message,
        error=error,
        meta=meta,
    )


async def _get_pdf_path_for_index(uow: SqlAlchemyUnitOfWork, *, project_id: UUID, document_id: UUID) -> Path:
    project = await uow.project_repo.get_by_id(project_id)  # <- adapt to your API
    if not project.primary_document or project.primary_document.id != document_id:
        raise RuntimeError("Document not found for project")
    return Path(project.primary_document.storage_path)


def _batched(items: list[str], batch_size: int) -> list[list[str]]:
    if batch_size <= 0:
        batch_size = 64
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


async def run_indexing(*, index_id: UUID) -> None:
    # 1) Read index + mark running + capture embed_cfg while session is alive
    async with SessionLocal() as session:
        uow = SqlAlchemyUnitOfWork(session)
        async with uow:
            idx = await uow.index_repo.get_by_id(index_id=index_id)
            if not idx:
                return

            if idx.cancel_requested:
                await uow.index_repo.delete_index_artifacts(index_id=index_id)
                await uow.index_repo.update_progress(
                    index_id=index_id,
                    status=IndexStatus.CANCELLED,
                    progress=0,
                    message="Cancelled",
                )
                return

            # capture config NOW
            embed_cfg: EmbedConfig = idx.embed_config  # domain VO (best)
            # if your idx stores dict instead, do:
            # embed_cfg = EmbedConfig.from_dict(idx.embed_config)

            await uow.index_repo.update_progress(
                index_id=index_id,
                status=IndexStatus.RUNNING,
                progress=5,
                message="Loading document",
                meta={"embedder": embed_cfg.model},
            )

            pdf_path = await _get_pdf_path_for_index(uow, project_id=idx.project_id, document_id=idx.document_id)

    # 2) Extract text (outside txn)
    try:
        text = extract_text_from_pdf(pdf_path)
    except Exception as e:
        async with SessionLocal() as session:
            uow = SqlAlchemyUnitOfWork(session)
            async with uow:
                await uow.index_repo.update_progress(
                    index_id=index_id,
                    status=IndexStatus.FAILED,
                    progress=0,
                    message="Failed to extract text",
                    error=str(e),
                )
        return

    # 3) Chunk
    chunks = chunk_text(text, max_chars=1200, overlap=150)
    texts = [c[0] for c in chunks]

    async with SessionLocal() as session:
        uow = SqlAlchemyUnitOfWork(session)
        async with uow:
            if await uow.index_repo.is_cancel_requested(index_id=index_id):
                await uow.index_repo.delete_index_artifacts(index_id=index_id)
                await uow.index_repo.update_progress(
                    index_id=index_id,
                    status=IndexStatus.CANCELLED,
                    progress=0,
                    message="Cancelled",
                )
                return

            await uow.index_repo.update_progress(
                index_id=index_id,
                status=IndexStatus.RUNNING,
                progress=20,
                message=f"Chunking ({len(chunks)} chunks)",
            )

            for chunk_text_value, meta in chunks:
                session.add(
                    ChunkModel(
                        index_id=index_id,
                        chunk_index=int(meta["chunk_index"]),
                        text=chunk_text_value,
                        meta=meta,
                    )
                )


    # 4) Embed (batched)
    embeddings = OpenAIEmbeddings(
        model=embed_cfg.model,
        dimensions=embed_cfg.dimensions,
        api_key=settings.OPENAI_API_KEY,
    )
    embedder = LangChainEmbedder(embeddings)

    vectors: list[list[float]] = []
    try:
        batches = _batched(texts, embed_cfg.batch_size)
        total = len(texts)
        done = 0

        # progress range for embedding, e.g. 35 -> 85
        start_p, end_p = 35, 85

        for bi, batch in enumerate(batches):
            # cancellation check between batches
            async with SessionLocal() as session:
                uow = SqlAlchemyUnitOfWork(session)
                async with uow:
                    if await uow.index_repo.is_cancel_requested(index_id=index_id):
                        await uow.index_repo.delete_index_artifacts(index_id=index_id)
                        await uow.index_repo.update_progress(
                            index_id=index_id,
                            status=IndexStatus.CANCELLED,
                            progress=0,
                            message="Cancelled",
                        )
                        return

                    # update progress before calling API
                    pct = start_p + int((done / max(1, total)) * (end_p - start_p))
                    await uow.index_repo.update_progress(
                        index_id=index_id,
                        status=IndexStatus.RUNNING,
                        progress=pct,
                        message=f"Embedding batch {bi+1}/{len(batches)}",
                        meta={"embedder": embed_cfg.model, "batch_size": embed_cfg.batch_size, "done": done, "total": total},
                    )

            batch_vectors = await embedder.aembed_documents(batch)
            vectors.extend(batch_vectors)
            done += len(batch)

    except Exception as e:
        async with SessionLocal() as session:
            uow = SqlAlchemyUnitOfWork(session)
            async with uow:
                await uow.index_repo.update_progress(
                    index_id=index_id,
                    status=IndexStatus.FAILED,
                    progress=35,
                    message="Embedding failed",
                    error=str(e),
                )
        return

    # At this point you have vectors aligned with texts/chunks:
    # vectors[i] corresponds to chunks[i]

    async with SessionLocal() as session:
        uow = SqlAlchemyUnitOfWork(session)
        async with uow:
            if await uow.index_repo.is_cancel_requested(index_id=index_id):
                await uow.index_repo.delete_index_artifacts(index_id=index_id)
                await uow.index_repo.update_progress(
                    index_id=index_id,
                    status=IndexStatus.CANCELLED,
                    progress=0,
                    message="Cancelled",
                )
                return


            await uow.index_repo.update_progress(
                index_id=index_id,
                status=IndexStatus.READY,
                progress=100,
                message="Index ready",
                meta={"chunks": len(chunks), "embedder": embed_cfg.model},
            )

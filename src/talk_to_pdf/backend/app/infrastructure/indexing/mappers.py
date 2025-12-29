from __future__ import annotations

from typing import Any, Iterable
from uuid import UUID

from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig, ChunkDraft, ChunkEmbeddingDraft, \
    ChunkMatch
from talk_to_pdf.backend.app.infrastructure.db.models.indexing import DocumentIndexModel, ChunkModel


def index_model_to_domain(m: DocumentIndexModel) -> DocumentIndex:
    return DocumentIndex(
        id=m.id,
        project_id=m.project_id,
        document_id=m.document_id,
        storage_path=m.storage_path,
        chunker_version=m.chunker_version,
        embed_config=EmbedConfig.from_dict(m.embed_config),
        status=m.status,
        progress=m.progress,
        message=m.message,
        error=m.error,
        cancel_requested=m.cancel_requested,
        updated_at=m.updated_at,
    )


def create_document_index_model(*,
        project_id: UUID,
        document_id: UUID,
        storage_path:str,
        chunker_version: str,
        embed_config:EmbedConfig) -> DocumentIndexModel:
    return DocumentIndexModel(
        project_id=project_id,
        document_id=document_id,
        storage_path=storage_path,
        status=IndexStatus.PENDING,
        progress=0,
        message="Queued",
        error=None,
        cancel_requested=False,
        chunker_version=chunker_version,
        embed_config=embed_config.to_dict(),
        embed_signature=embed_config.signature(),
        meta=None,
    )

def create_chunk_models(index_id:UUID,chunks:list[ChunkDraft])->list[ChunkModel]:
    models = [
        ChunkModel(
            index_id=index_id,
            chunk_index=c.chunk_index,
            text=c.text,
            meta=c.meta,
        )
        for c in chunks
    ]
    return models


def embedding_drafts_to_insert_rows(
    *,
    index_id: UUID,
    embed_signature: str,
    embeddings: list[ChunkEmbeddingDraft],
) -> list[dict[str, Any]]:
    """
    Map domain embedding drafts to DB insert rows (dicts) for ChunkEmbeddingModel.

    Kept out of the repository so the repo stays focused on persistence mechanics.
    """
    return [
        {
            "index_id": index_id,
            "chunk_id": e.chunk_id,
            "chunk_index": e.chunk_index,
            "embed_signature": embed_signature,
            "embedding": list(e.vector.values),  # pgvector expects list[float]
            # "meta": e.meta,  # only if your model has it
        }
        for e in embeddings
    ]

def rows_to_chunk_matches(rows: Iterable[object]) -> list[ChunkMatch]:
    """
    Map raw SQLAlchemy result rows to domain ChunkMatch objects.

    Assumes each row exposes:
      - chunk_id
      - chunk_index
      - score
    """
    return [
        ChunkMatch(
            chunk_id=row.chunk_id,
            chunk_index=row.chunk_index,
            score=float(row.score),
        )
        for row in rows
    ]
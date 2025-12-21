from __future__ import annotations

from uuid import UUID

from talk_to_pdf.backend.app.domain.indexing.entities import DocumentIndex
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig
from talk_to_pdf.backend.app.infrastructure.indexing.models import DocumentIndexModel


def index_model_to_domain(m: DocumentIndexModel) -> DocumentIndex:
    return DocumentIndex(
        id=m.id,
        project_id=m.project_id,
        document_id=m.document_id,
        chunker_version=m.chunker_version,
        embed_config=EmbedConfig.from_dict(m.embed_config),
        status=m.status,
        progress=m.progress,
        message=m.message,
        error=m.error,
        cancel_requested=m.cancel_requested,
        updated_at=m.updated_at,
    )


def create_document_index_model(
        project_id: UUID,
        document_id: UUID,
        chunker_version: str,
        embed_config:EmbedConfig) -> DocumentIndexModel:
    return DocumentIndexModel(
        project_id=project_id,
        document_id=document_id,
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
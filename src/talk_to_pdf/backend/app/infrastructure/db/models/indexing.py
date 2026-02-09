from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import Enum as SAEnum, UniqueConstraint, Computed, Index
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector as PGVector

from talk_to_pdf.backend.app.domain.common import utcnow
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.infrastructure.db.base import Base




class DocumentIndexModel(Base):
    __tablename__ = "document_indexes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    project_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    document_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[IndexStatus] = mapped_column(
        SAEnum(
            IndexStatus,
            name="index_status_enum",
            native_enum=True,  # PostgreSQL ENUM
            create_constraint=True,
        ),
        nullable=False,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # optional but recommended for reproducibility / re-indexing later
    chunker_version: Mapped[str] = mapped_column(String(64), nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    embed_config: Mapped[dict ] = mapped_column(JSONB, nullable=False)
    embed_signature: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    chunks: Mapped[list["ChunkModel"]] = relationship(
        back_populates="index",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ChunkModel(Base):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    index_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_indexes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    # NEW: normalized text used for better retrieval (de-hyphenate, newline cleanup, etc.)
    text_norm: Mapped[str | None] = mapped_column(Text, nullable=True)

    # NEW: full-text search vector (generated, always in sync)
    tsv: Mapped[str] = mapped_column(
        TSVECTOR(),
        Computed("to_tsvector('english', coalesce(text_norm, text))", persisted=True),
        nullable=False,
    )

    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    index: Mapped["DocumentIndexModel"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("index_id", "chunk_index", name="uq_chunks_index_chunk_index"),
        # NEW: GIN index for FTS
        Index("ix_chunks_tsv_gin", "tsv", postgresql_using="gin"),
    )


class ChunkEmbeddingModel(Base):
    __tablename__ = "chunk_embeddings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    index_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_indexes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # optional but helpful for debugging + quick ordering
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # pgvector column
    embedding: Mapped[list[float]] = mapped_column(PGVector(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    embed_signature: Mapped[str] = mapped_column(String(64), nullable=False,index=True)
    __table_args__ = (
        UniqueConstraint("index_id", "chunk_id","embed_signature", name="uq_chunk_embeddings_index_chunk"),
    )
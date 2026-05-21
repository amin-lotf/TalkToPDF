from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest

from talk_to_pdf.backend.app.api.v1.indexing.deps import get_chunker_version
from talk_to_pdf.backend.app.application.indexing.dto import StartIndexingInputDTO
from talk_to_pdf.backend.app.application.indexing.use_cases.start_indexing import StartIndexingUseCase
from talk_to_pdf.backend.app.application.projects.dto import CreateProjectInputDTO
from talk_to_pdf.backend.app.application.projects.use_cases.create_project import CreateProjectUseCase
from talk_to_pdf.backend.app.core.config import settings
from talk_to_pdf.backend.app.core.deps import get_embed_config
from talk_to_pdf.backend.app.infrastructure.common.token_counter import count_tokens
from talk_to_pdf.backend.app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage
from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.block_chunker import DefaultBlockChunker
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.grobid_pdf_to_xml import GrobidPdfToXmlConverter
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.grobid_tei_block_extractor import GrobidTeiBlockExtractor
from talk_to_pdf.backend.app.infrastructure.indexing.service import IndexingWorkerService, WorkerDeps

RUN_FLAG = "RUN_CHUNKING_INSPECTION"

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv(RUN_FLAG) != "1",
        reason=(
            "Manual inspection utility. "
            f"Set {RUN_FLAG}=1 to generate scripts/results.md."
        ),
    ),
]

RESULTS_PATH = Path("scripts/results.md")
SOURCE_PDF_PATH = Path("scripts/BMW_Group.pdf")


@dataclass
class NoopRunner:
    async def enqueue(self, *, index_id: UUID) -> None:
        return


@dataclass
class UnusedEmbedderFactory:
    def create(self, cfg):  # pragma: no cover - defensive only
        raise AssertionError("Embedding should not run in chunking inspection")


async def _require_grobid() -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.GROBID_URL.rstrip('/')}/api/isalive")
    except httpx.HTTPError as exc:
        pytest.skip(f"GROBID is unavailable at {settings.GROBID_URL}: {exc}")

    if response.status_code != 200:
        pytest.skip(
            f"GROBID health check failed at {settings.GROBID_URL}: HTTP {response.status_code}"
        )


async def _create_project_and_index(*, uow, tmp_path: Path, pdf_bytes: bytes) -> tuple[FilesystemFileStorage, Any, UUID]:
    embed_cfg = get_embed_config()
    file_storage = FilesystemFileStorage(base_dir=tmp_path)

    project_out = await CreateProjectUseCase(uow=uow, file_storage=file_storage).execute(
        CreateProjectInputDTO(
            owner_id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Chunking Inspection",
            file_bytes=pdf_bytes,
            filename=SOURCE_PDF_PATH.name,
            content_type="application/pdf",
        )
    )

    await StartIndexingUseCase(
        uow=uow,
        runner=NoopRunner(),
        chunker_version=get_chunker_version(),
        embed_config=embed_cfg,
    ).execute(
        StartIndexingInputDTO(
            owner_id=project_out.owner_id,
            project_id=project_out.id,
            document_id=project_out.primary_document.id,
        )
    )

    async with uow:
        idx = await uow.index_repo.get_latest_active_by_project_and_signature(
            project_id=project_out.id,
            embed_signature=embed_cfg.signature(),
        )
        assert idx is not None
        return file_storage, project_out, idx.id


def _build_real_chunking_worker(*, session, file_storage: FilesystemFileStorage) -> IndexingWorkerService:
    def session_factory():
        class _SessionContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return _SessionContext()

    def uow_factory(db_session):
        return SqlAlchemyUnitOfWork(db_session)

    return IndexingWorkerService(
        WorkerDeps(
            pdf_to_xml_converter=GrobidPdfToXmlConverter(base_url=settings.GROBID_URL),
            block_extractor=GrobidTeiBlockExtractor(),
            block_chunker=DefaultBlockChunker(
                max_chars=settings.CHUNKER_MAX_CHARS,
                overlap_chars=settings.CHUNKER_OVERLAP,
            ),
            embedder_factory=UnusedEmbedderFactory(),
            session_factory=session_factory,
            uow_factory=uow_factory,
            file_storage=file_storage,
        )
    )


def _page_label(meta: dict[str, Any] | None) -> str:
    if not meta:
        return "n/a"

    for key in ("page", "page_number", "page_start", "page_end", "page_range"):
        value = meta.get(key)
        if value not in (None, "", []):
            return str(value)

    pages: set[str] = set()
    for block in meta.get("blocks", []):
        if not isinstance(block, dict):
            continue
        block_meta = block.get("meta") or {}
        for key in ("page", "page_number", "page_start", "page_end", "page_range"):
            value = block_meta.get(key)
            if value not in (None, "", []):
                pages.add(str(value))

    if not pages:
        return "n/a"
    return ", ".join(sorted(pages))


def _section_label(meta: dict[str, Any] | None) -> str:
    if not meta:
        return "n/a"

    dominant = meta.get("dominant_head")
    if dominant:
        return str(dominant)

    for block in meta.get("blocks", []):
        if not isinstance(block, dict):
            continue
        head = (block.get("meta") or {}).get("head")
        if head:
            return str(head)

    return "n/a"


def _metadata_json(meta: dict[str, Any] | None) -> str:
    return json.dumps(meta or {}, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def _render_report(*, source_name: str, chunker_version: str, chunks) -> str:
    lines = [
        "# Chunking Inspection Result",
        "",
        f"Source PDF: {source_name}",
        f"Chunker Version: {chunker_version}",
        f"Token Model: {settings.EMBED_MODEL}",
        f"Total chunks: {len(chunks)}",
        "",
        "---",
    ]

    for position, chunk in enumerate(chunks, start=1):
        meta = chunk.meta or {}
        lines.extend(
            [
                "",
                f"## Chunk {position}",
                "",
                f"**Chunk ID:** {chunk.id}",
                f"**Chunk Index:** {chunk.chunk_index}",
                f"**Page:** {_page_label(meta)}",
                f"**Section:** {_section_label(meta)}",
                f"**Characters:** {len(chunk.text)}",
                f"**Tokens:** {count_tokens(chunk.text, model=settings.EMBED_MODEL)}",
                "",
                "### Metadata",
                "",
                "```json",
                _metadata_json(meta),
                "```",
                "",
                "### Text",
                "",
                "~~~text",
                chunk.text,
                "~~~",
                "",
                "---",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


async def test_write_chunking_inspection_markdown(session, uow, pdf_bytes, tmp_path: Path):
    """
    Manual inspection utility only.
    This test intentionally writes a markdown artifact and does not assert chunk quality.
    """
    await _require_grobid()

    file_storage, _, index_id = await _create_project_and_index(
        uow=uow,
        tmp_path=tmp_path,
        pdf_bytes=pdf_bytes,
    )
    worker = _build_real_chunking_worker(session=session, file_storage=file_storage)

    async with uow:
        loaded = await worker.load_index_metadata(uow=uow, index_id=index_id)
        assert loaded is not None
        _, _, _, storage_path = loaded

    xml = await worker.convert_pdf_to_xml(storage_path=storage_path)
    blocks = await worker.extract_blocks_from_xml(xml)
    await worker.create_and_store_chunks(index_id=index_id, blocks=blocks)

    async with uow:
        chunks = await uow.chunk_repo.list_chunks_for_index(index_id=index_id)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        _render_report(
            source_name=SOURCE_PDF_PATH.name,
            chunker_version=get_chunker_version(),
            chunks=chunks,
        ),
        encoding="utf-8",
    )

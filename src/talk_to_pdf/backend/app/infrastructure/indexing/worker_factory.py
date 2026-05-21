from __future__ import annotations

from pathlib import Path

from talk_to_pdf.backend.app.core.config import Settings, settings
from talk_to_pdf.backend.app.infrastructure.common.embedders.factory_openai_langchain import OpenAIEmbedderFactory
from talk_to_pdf.backend.app.infrastructure.db.session import SessionLocal
from talk_to_pdf.backend.app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage
from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.azure_markdown_block_chunker import AzureMarkdownBlockChunker
from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.block_chunker import DefaultBlockChunker
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.azure_document_intelligence_block_extractor import (
    AzureDocumentIntelligenceBlockExtractor,
)
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.grobid_pdf_block_extractor import GrobidPdfBlockExtractor
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.grobid_pdf_to_xml import GrobidPdfToXmlConverter
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.grobid_tei_block_extractor import GrobidTeiBlockExtractor
from talk_to_pdf.backend.app.infrastructure.indexing.service import IndexingWorkerService, WorkerDeps


def _build_pdf_extraction_components(*, app_settings: Settings, file_storage: FilesystemFileStorage):
    provider = app_settings.PDF_EXTRACTION_PROVIDER

    if provider == "grobid":
        return (
            GrobidPdfBlockExtractor(
                file_storage=file_storage,
                pdf_to_xml_converter=GrobidPdfToXmlConverter(base_url=app_settings.GROBID_URL),
                xml_block_extractor=GrobidTeiBlockExtractor(),
            ),
            DefaultBlockChunker(
                max_chars=app_settings.CHUNKER_MAX_CHARS,
                overlap_chars=app_settings.CHUNKER_OVERLAP,
            ),
        )

    if provider == "azure_document_intelligence":
        return (
            AzureDocumentIntelligenceBlockExtractor(
                file_storage=file_storage,
                endpoint=app_settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or "",
                api_key=app_settings.AZURE_DOCUMENT_INTELLIGENCE_KEY or "",
                model_id=app_settings.AZURE_DOCUMENT_INTELLIGENCE_MODEL,
                output_format=app_settings.AZURE_DOCUMENT_INTELLIGENCE_OUTPUT_FORMAT,
            ),
            AzureMarkdownBlockChunker(
                max_chars=app_settings.CHUNKER_MAX_CHARS,
                overlap_chars=app_settings.CHUNKER_OVERLAP,
            ),
        )

    raise ValueError(f"Unsupported PDF extraction provider: {provider}")


def build_worker(*, app_settings: Settings | None = None) -> IndexingWorkerService:
    app_settings = app_settings or settings
    file_storage = FilesystemFileStorage(base_dir=Path(app_settings.FILE_STORAGE_DIR))
    pdf_block_extractor, block_chunker = _build_pdf_extraction_components(
        app_settings=app_settings,
        file_storage=file_storage,
    )

    deps = WorkerDeps(
        pdf_block_extractor=pdf_block_extractor,
        block_chunker=block_chunker,
        embedder_factory=OpenAIEmbedderFactory(api_key=app_settings.OPENAI_API_KEY or ""),
        session_factory=SessionLocal,
        uow_factory=SqlAlchemyUnitOfWork,
    )
    return IndexingWorkerService(deps)

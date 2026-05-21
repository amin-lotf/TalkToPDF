from __future__ import annotations

import pytest
from pydantic import ValidationError

from talk_to_pdf.backend.app.core.config import Settings
from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.azure_markdown_block_chunker import (
    AzureMarkdownBlockChunker,
)
from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.block_chunker import DefaultBlockChunker
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.azure_document_intelligence_block_extractor import (
    AzureDocumentIntelligenceBlockExtractor,
)
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.grobid_pdf_block_extractor import (
    GrobidPdfBlockExtractor,
)
from talk_to_pdf.backend.app.infrastructure.indexing.worker_factory import _build_pdf_extraction_components
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage


def test_worker_factory_selects_grobid_provider(tmp_path):
    app_settings = Settings(
        _env_file=None,
        OPENAI_API_KEY="test-openai-key",
        FILE_STORAGE_DIR=str(tmp_path),
        PDF_EXTRACTION_PROVIDER="grobid",
    )
    file_storage = FilesystemFileStorage(base_dir=tmp_path)

    extractor, chunker = _build_pdf_extraction_components(
        app_settings=app_settings,
        file_storage=file_storage,
    )

    assert isinstance(extractor, GrobidPdfBlockExtractor)
    assert isinstance(chunker, DefaultBlockChunker)


def test_worker_factory_selects_azure_document_intelligence_provider(tmp_path):
    app_settings = Settings(
        _env_file=None,
        OPENAI_API_KEY="test-openai-key",
        FILE_STORAGE_DIR=str(tmp_path),
        PDF_EXTRACTION_PROVIDER="azure_document_intelligence",
        AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://example.cognitiveservices.azure.com/",
        AZURE_DOCUMENT_INTELLIGENCE_KEY="test-key",
    )
    file_storage = FilesystemFileStorage(base_dir=tmp_path)

    extractor, chunker = _build_pdf_extraction_components(
        app_settings=app_settings,
        file_storage=file_storage,
    )

    assert isinstance(extractor, AzureDocumentIntelligenceBlockExtractor)
    assert isinstance(chunker, AzureMarkdownBlockChunker)


def test_settings_require_azure_document_intelligence_config():
    with pytest.raises(ValidationError) as exc:
        Settings(
            _env_file=None,
            OPENAI_API_KEY="test-openai-key",
            PDF_EXTRACTION_PROVIDER="azure_document_intelligence",
            AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="",
            AZURE_DOCUMENT_INTELLIGENCE_KEY="",
        )

    error_text = str(exc.value)
    assert "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT" in error_text
    assert "AZURE_DOCUMENT_INTELLIGENCE_KEY" in error_text

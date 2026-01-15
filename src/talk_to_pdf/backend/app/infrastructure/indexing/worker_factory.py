from __future__ import annotations

from pathlib import Path

from talk_to_pdf.backend.app.core.config import settings
from talk_to_pdf.backend.app.infrastructure.common.embedders.factory_openai_langchain import OpenAIEmbedderFactory
from talk_to_pdf.backend.app.infrastructure.db.session import SessionLocal
from talk_to_pdf.backend.app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from talk_to_pdf.backend.app.infrastructure.files.filesystem_storage import FilesystemFileStorage
from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.simple_char_chunker import SimpleCharChunker
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.pypdf_extractor import PyPDFTextExtractor
from talk_to_pdf.backend.app.infrastructure.indexing.service import IndexingWorkerService, WorkerDeps


def build_worker() -> IndexingWorkerService:
    deps = WorkerDeps(
        extractor=PyPDFTextExtractor(),
        chunker=SimpleCharChunker(max_chars=settings.CHUNKER_MAX_CHARS, overlap=settings.CHUNKER_OVERLAP),
        embedder_factory=OpenAIEmbedderFactory(api_key=settings.OPENAI_API_KEY),
        session_factory=SessionLocal,
        uow_factory=SqlAlchemyUnitOfWork,
        file_storage=FilesystemFileStorage(base_dir=Path(settings.FILE_STORAGE_DIR)),
    )
    return IndexingWorkerService(deps)

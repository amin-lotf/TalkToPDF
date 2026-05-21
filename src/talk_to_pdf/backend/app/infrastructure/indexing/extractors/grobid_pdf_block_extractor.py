from __future__ import annotations

import asyncio

from talk_to_pdf.backend.app.application.indexing.interfaces import PdfToXmlConverter, XmlBlockExtractor
from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.indexing.value_objects import Block


class GrobidPdfBlockExtractor:
    def __init__(
        self,
        *,
        file_storage: FileStorage,
        pdf_to_xml_converter: PdfToXmlConverter,
        xml_block_extractor: XmlBlockExtractor,
    ) -> None:
        self._file_storage = file_storage
        self._pdf_to_xml_converter = pdf_to_xml_converter
        self._xml_block_extractor = xml_block_extractor

    async def extract(self, *, storage_path: str) -> list[Block]:
        try:
            pdf_bytes = await self._file_storage.read_bytes(storage_path=storage_path)
        except Exception as e:
            raise RuntimeError("Failed to read PDF file") from e

        try:
            xml = await asyncio.to_thread(self._pdf_to_xml_converter.convert, content=pdf_bytes)
        except Exception as e:
            raise RuntimeError("Failed to convert PDF to TEI XML") from e

        try:
            return await asyncio.to_thread(self._xml_block_extractor.extract, xml=xml)
        except Exception as e:
            raise RuntimeError("Failed to parse TEI XML into blocks") from e

from __future__ import annotations

from pathlib import Path
from typing import List

from talk_to_pdf.backend.app.core import settings


class PyPDFTextExtractor:
    def extract(self, *, content: bytes) -> str:
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(content))
        parts: List[str] = []

        for page in reader.pages:
            parts.append(page.extract_text() or "")

        return "\n".join(parts).strip()

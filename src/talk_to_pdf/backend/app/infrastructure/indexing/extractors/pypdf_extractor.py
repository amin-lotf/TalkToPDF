from __future__ import annotations

from pathlib import Path
from typing import List


class PyPDFTextExtractor:
    def extract(self, pdf_path: Path) -> str:
        from pypdf import PdfReader  # local import keeps import light

        reader = PdfReader(str(pdf_path))
        parts: List[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()

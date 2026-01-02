from __future__ import annotations

from dataclasses import dataclass
from typing import List

from talk_to_pdf.backend.app.domain.indexing.value_objects import ChunkDraft


@dataclass(frozen=True, slots=True)
class SimpleCharChunker:
    max_chars: int
    overlap: int

    def chunk(self, *,text: str) -> list[ChunkDraft]:
        text = text.strip()
        if not text:
            return []

        chunks: List[ChunkDraft] = []
        start = 0
        n = len(text)
        chunk_idx = 0

        while start < n:
            end = min(start + self.max_chars, n)
            chunk = text[start:end].strip()
            if chunk:
                meta = {"char_start": start, "char_end": end, "chunk_index": chunk_idx}
                chunks.append(ChunkDraft(chunk_index=chunk_idx, text=chunk, meta=meta))
                chunk_idx += 1

            if end >= n:
                break
            start = max(0, end - self.overlap)

        return chunks


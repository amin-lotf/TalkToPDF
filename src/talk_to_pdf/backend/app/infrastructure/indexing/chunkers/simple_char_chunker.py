from __future__ import annotations

from dataclasses import dataclass
from typing import List

from talk_to_pdf.backend.app.domain.indexing.value_objects import Block, ChunkDraft


@dataclass(frozen=True, slots=True)
class SimpleCharChunker:
    max_chars: int
    overlap: int

    def chunk(self, *, blocks: list[Block]) -> list[ChunkDraft]:
        text = "\n\n".join(b.text for b in blocks if b.text).strip()
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
                blocks = [
                    Block(
                        text=chunk,
                        meta={
                            "kind": "unknown",
                            "div_index": 0,
                            "head": None,
                            "xml_id": None,
                            "targets": [],
                            **meta,
                        },
                    )
                ]
                chunks.append(ChunkDraft(chunk_index=chunk_idx, blocks=blocks, text=chunk, meta=meta))
                chunk_idx += 1

            if end >= n:
                break
            start = max(0, end - self.overlap)

        return chunks

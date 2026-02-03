from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from talk_to_pdf.backend.app.domain.indexing.value_objects import Block, ChunkDraft


@dataclass(frozen=True, slots=True)
class DefaultBlockChunker:
    max_chars: int = 1200

    def chunk(self, *, blocks: list[Block]) -> list[ChunkDraft]:
        prepared = [b for b in blocks if b.text and b.text.strip()]
        if not prepared:
            return []

        chunks: list[ChunkDraft] = []
        buf_blocks: list[Block] = []
        buf_texts: list[str] = []
        buf_len = 0
        chunk_idx = 0

        def flush() -> None:
            nonlocal buf_blocks, buf_texts, buf_len, chunk_idx
            if not buf_blocks:
                return
            text = "\n\n".join(buf_texts).strip()
            meta = self._chunk_meta(buf_blocks, chunk_idx, text)
            chunks.append(
                ChunkDraft(
                    chunk_index=chunk_idx,
                    blocks=list(buf_blocks),
                    text=text,
                    meta=meta,
                )
            )
            chunk_idx += 1
            buf_blocks = []
            buf_texts = []
            buf_len = 0

        for block in prepared:
            rendered = self._render_block(block)
            if not rendered:
                continue

            if self._is_section_head(block):
                flush()
                buf_blocks.append(block)
                buf_texts.append(rendered)
                buf_len = len(rendered)
                continue

            sep = 2 if buf_texts else 0
            candidate_len = buf_len + sep + len(rendered)
            keep_with_head = buf_blocks and self._is_section_head(buf_blocks[-1]) and len(buf_blocks) == 1

            if buf_blocks and candidate_len > self.max_chars and not keep_with_head:
                flush()

            if buf_blocks:
                buf_texts.append(rendered)
                buf_blocks.append(block)
                buf_len = buf_len + (2 if buf_texts else 0) + len(rendered)
            else:
                buf_blocks = [block]
                buf_texts = [rendered]
                buf_len = len(rendered)

        flush()
        return chunks

    def _render_block(self, block: Block) -> str:
        meta = block.meta or {}
        kind = meta.get("kind")
        text = (block.text or "").strip()
        if not text:
            return ""
        if kind == "section_head":
            return f"## {text}"
        if kind == "equation":
            label = meta.get("equation_label")
            prefix = f"({label}) " if label else ""
            return f"{prefix}{text}"
        if kind == "list_item":
            return f"- {text}"
        if kind == "figure_caption":
            return f"Figure: {text}"
        if kind == "table":
            return f"Table: {text}"
        return text

    def _chunk_meta(self, blocks: list[Block], chunk_idx: int, text: str) -> dict:
        heads = [b.meta.get("head") for b in blocks if b.meta and b.meta.get("head")]
        divs = [b.meta.get("div_index") for b in blocks if b.meta and isinstance(b.meta.get("div_index"), int)]
        kinds = [b.meta.get("kind", "unknown") for b in blocks if b.meta]
        meta = {
            "chunk_index": chunk_idx,
            "chunk_char_len": len(text),
            "dominant_head": heads[-1] if heads else None,
        }
        if divs:
            meta["div_range"] = [min(divs), max(divs)]
        if kinds:
            meta["block_counts"] = dict(Counter(kinds))
        return meta

    @staticmethod
    def _is_section_head(block: Block) -> bool:
        return (block.meta or {}).get("kind") == "section_head"


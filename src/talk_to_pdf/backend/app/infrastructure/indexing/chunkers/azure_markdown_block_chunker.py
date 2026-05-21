from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

from talk_to_pdf.backend.app.domain.indexing.value_objects import Block, ChunkDraft
from talk_to_pdf.backend.app.infrastructure.indexing.text_normalizer import normalize_block_text_by_kind

FlushReason = Literal["size", "section", "end"]
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")


@dataclass(frozen=True, slots=True)
class AzureMarkdownBlockChunker:
    max_chars: int = 1200
    overlap_chars: int = 200

    SPLITTABLE_BLOCK_TYPES: tuple[str, ...] = ("paragraph", "list_item")

    def chunk(self, *, blocks: list[Block]) -> list[ChunkDraft]:
        prepared = [block for block in blocks if (block.text or "").strip()]
        if not prepared:
            return []

        prepared = self._split_oversize_blocks(prepared)
        chunks: list[ChunkDraft] = []
        overlap_budget = max(0, min(self.overlap_chars, max(0, self.max_chars // 3)))

        buf_blocks: list[Block] = []
        buf_texts: list[str] = []
        buf_text_norms: list[str] = []
        buf_len = 0
        chunk_idx = 0
        current_section_key: tuple[str, ...] | None = None

        def flush(reason: FlushReason) -> None:
            nonlocal buf_blocks, buf_texts, buf_text_norms, buf_len, chunk_idx
            if not buf_blocks:
                return

            real_content = [
                block for block in buf_blocks
                if self._block_type(block) != "heading"
            ]
            if not real_content:
                buf_blocks = []
                buf_texts = []
                buf_text_norms = []
                buf_len = 0
                return

            text = self._join_texts(buf_texts)
            text_norm = self._join_texts(buf_text_norms)
            if not text:
                buf_blocks = []
                buf_texts = []
                buf_text_norms = []
                buf_len = 0
                return

            meta = self._chunk_meta(blocks_in_chunk=buf_blocks, idx=chunk_idx, text=text)
            chunks.append(
                ChunkDraft(
                    chunk_index=chunk_idx,
                    blocks=list(buf_blocks),
                    text=text,
                    text_norm=text_norm,
                    meta=meta,
                )
            )
            chunk_idx += 1

            if reason == "size" and overlap_budget > 0:
                ov_blocks, ov_texts, ov_text_norms, ov_len = self._carry_overlap_suffix(
                    prev_blocks=buf_blocks,
                    prev_texts=buf_texts,
                    prev_text_norms=buf_text_norms,
                    budget=overlap_budget,
                )
                if ov_blocks:
                    buf_blocks = ov_blocks
                    buf_texts = ov_texts
                    buf_text_norms = ov_text_norms
                    buf_len = ov_len
                    return

            buf_blocks = []
            buf_texts = []
            buf_text_norms = []
            buf_len = 0

        def ensure_fit(rendered_next: str) -> None:
            nonlocal buf_blocks, buf_texts, buf_text_norms, buf_len
            sep = 2 if buf_texts else 0
            if buf_len + sep + len(rendered_next) <= self.max_chars:
                return

            while buf_blocks:
                first = buf_blocks[0]
                if (first.meta or {}).get("synthetic_kind") != "overlap_block":
                    break
                buf_blocks.pop(0)
                buf_texts.pop(0)
                buf_text_norms.pop(0)
                buf_len = len(self._join_texts(buf_texts))

            sep = 2 if buf_texts else 0
            if buf_blocks and buf_len + sep + len(rendered_next) > self.max_chars:
                flush("size")

        for block in prepared:
            block_section_key = tuple(self._section_path(block))
            if current_section_key is None:
                current_section_key = block_section_key
            elif self._block_type(block) == "heading" and block_section_key != current_section_key:
                flush("section")
                current_section_key = block_section_key

            rendered = self._render_block(block)
            if not rendered:
                continue

            if self._block_type(block) == "heading":
                flush("section")
                buf_blocks = [block]
                buf_texts = [rendered]
                buf_text_norms = [normalize_block_text_by_kind(rendered, kind="section_head")]
                buf_len = len(rendered)
                current_section_key = block_section_key
                continue

            if len(rendered) > self.max_chars:
                flush("size")
                meta = self._chunk_meta(blocks_in_chunk=[block], idx=chunk_idx, text=rendered)
                meta["oversize_single_block"] = True
                meta["max_chars"] = self.max_chars
                chunks.append(
                    ChunkDraft(
                        chunk_index=chunk_idx,
                        blocks=[block],
                        text=rendered,
                        text_norm=normalize_block_text_by_kind(rendered, kind="non-splittable"),
                        meta=meta,
                    )
                )
                chunk_idx += 1
                buf_blocks = []
                buf_texts = []
                buf_text_norms = []
                buf_len = 0
                continue

            ensure_fit(rendered)

            sep = 2 if buf_texts else 0
            if buf_blocks and buf_len + sep + len(rendered) > self.max_chars:
                flush("size")
                ensure_fit(rendered)

            sep = 2 if buf_texts else 0
            buf_blocks.append(block)
            buf_texts.append(rendered)
            buf_text_norms.append(block.text_norm or normalize_block_text_by_kind(rendered, kind=self._normalizer_kind(block)))
            buf_len += sep + len(rendered)

        flush("end")
        return chunks

    def _split_oversize_blocks(self, blocks: list[Block]) -> list[Block]:
        out: list[Block] = []
        for block in blocks:
            rendered = self._render_block(block)
            block_type = self._block_type(block)
            if len(rendered) <= self.max_chars or block_type not in self.SPLITTABLE_BLOCK_TYPES:
                out.append(block)
                continue

            spans = self._split_text_sentence_aware(block.text, self.max_chars)
            base_meta = dict(block.meta or {})
            base_meta["synthetic"] = True
            base_meta["synthetic_kind"] = "split_block"
            base_meta["split_kind"] = block_type
            base_meta["split_count"] = len(spans)

            for split_index, (start, end) in enumerate(spans):
                sub_text = block.text[start:end].strip()
                if not sub_text:
                    continue
                sub_meta = dict(base_meta)
                sub_meta["split_index"] = split_index
                sub_meta["char_start"] = start
                sub_meta["char_end"] = end
                out.append(
                    Block(
                        text=sub_text,
                        text_norm=normalize_block_text_by_kind(
                            sub_text,
                            kind="paragraph" if block_type == "paragraph" else "list_item",
                        ),
                        meta=sub_meta,
                    )
                )
        return out

    def _split_text_sentence_aware(self, text: str, max_len: int) -> list[tuple[int, int]]:
        stripped = text.strip()
        if len(stripped) <= max_len:
            return [(0, len(stripped))]

        parts = [part.strip() for part in _SENTENCE_SPLIT_RE.split(stripped) if part.strip()]
        if len(parts) <= 1:
            return [(i, min(i + max_len, len(stripped))) for i in range(0, len(stripped), max_len)]

        spans: list[tuple[int, int]] = []
        cursor = 0
        current_start = 0
        current_len = 0

        for part in parts:
            found = stripped.find(part, cursor)
            if found == -1:
                found = cursor
            part_end = found + len(part)
            cursor = part_end

            if current_len == 0 and part_end - current_start > max_len:
                for i in range(current_start, part_end, max_len):
                    spans.append((i, min(i + max_len, part_end)))
                current_start = part_end
                current_len = 0
                continue

            candidate_len = part_end - current_start
            if candidate_len > max_len and current_len > 0:
                spans.append((current_start, found))
                current_start = found
                current_len = part_end - current_start
            else:
                current_len = candidate_len

        if current_start < len(stripped):
            tail = len(stripped) - current_start
            if tail <= max_len:
                spans.append((current_start, len(stripped)))
            else:
                for i in range(current_start, len(stripped), max_len):
                    spans.append((i, min(i + max_len, len(stripped))))
        return spans

    def _chunk_meta(self, *, blocks_in_chunk: list[Block], idx: int, text: str) -> dict[str, Any]:
        real_blocks = [
            block for block in blocks_in_chunk
            if (block.meta or {}).get("synthetic_kind") != "overlap_block"
        ]
        provider = next(
            (
                (block.meta or {}).get("provider")
                for block in real_blocks
                if (block.meta or {}).get("provider")
            ),
            "azure_document_intelligence",
        )
        section_path = next(
            (
                list((block.meta or {}).get("section_path") or [])
                for block in real_blocks
                if (block.meta or {}).get("section_path") is not None
            ),
            [],
        )
        page_values = [
            value
            for block in real_blocks
            for value in (
                (block.meta or {}).get("page_start"),
                (block.meta or {}).get("page_end"),
            )
            if isinstance(value, int)
        ]
        kinds = [self._block_type(block) for block in real_blocks]

        meta: dict[str, Any] = {
            "chunk_index": idx,
            "chunk_char_len": len(text),
            "provider": provider,
            "section_path": section_path,
        }
        if page_values:
            meta["page_start"] = min(page_values)
            meta["page_end"] = max(page_values)
        if kinds:
            meta["block_counts"] = dict(Counter(kinds))
        if section_path:
            meta["dominant_heading"] = section_path[-1]
        if any((block.meta or {}).get("synthetic_kind") == "overlap_block" for block in blocks_in_chunk):
            meta["has_overlap_prefix"] = True
            meta["overlap_chars_budget"] = self.overlap_chars
        return meta

    def _carry_overlap_suffix(
        self,
        *,
        prev_blocks: list[Block],
        prev_texts: list[str],
        prev_text_norms: list[str],
        budget: int,
    ) -> tuple[list[Block], list[str], list[str], int]:
        candidates: list[tuple[Block, str, str]] = []
        for block, text, text_norm in zip(prev_blocks, prev_texts, prev_text_norms):
            if self._block_type(block) == "heading":
                continue
            if (block.meta or {}).get("synthetic_kind") == "overlap_block":
                continue
            if self._block_type(block) == "table":
                continue
            if text.strip():
                candidates.append((block, text, text_norm))

        chosen: list[tuple[Block, str, str]] = []
        total = 0
        for block, text, text_norm in reversed(candidates):
            sep = 2 if chosen else 0
            next_total = total + sep + len(text)
            if next_total > budget:
                break
            chosen.append((block, text, text_norm))
            total = next_total
        chosen.reverse()

        overlap_blocks: list[Block] = []
        overlap_texts: list[str] = []
        overlap_text_norms: list[str] = []
        for block, text, text_norm in chosen:
            meta = dict(block.meta or {})
            meta["synthetic"] = True
            meta["synthetic_kind"] = "overlap_block"
            overlap_blocks.append(Block(text=block.text, text_norm=block.text_norm, meta=meta))
            overlap_texts.append(text)
            overlap_text_norms.append(text_norm)
        return overlap_blocks, overlap_texts, overlap_text_norms, total

    def _render_block(self, block: Block) -> str:
        text = (block.text or "").strip()
        if not text:
            return ""

        block_type = self._block_type(block)
        if block_type == "heading":
            level = int((block.meta or {}).get("heading_level") or 1)
            level = min(max(level, 1), 6)
            return f"{'#' * level} {text}"
        if block_type == "table":
            return text
        if block_type == "list_item":
            list_kind = (block.meta or {}).get("list_kind")
            if list_kind == "ordered":
                ordinal = (block.meta or {}).get("list_ordinal") or 1
                return f"{ordinal}. {text}"
            return f"- {text}"
        return text

    def _block_type(self, block: Block) -> str:
        return str((block.meta or {}).get("block_type") or (block.meta or {}).get("kind") or "paragraph")

    def _section_path(self, block: Block) -> list[str]:
        value = (block.meta or {}).get("section_path") or []
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    def _normalizer_kind(self, block: Block) -> str:
        block_type = self._block_type(block)
        if block_type == "heading":
            return "section_head"
        if block_type == "table":
            return "table"
        if block_type == "list_item":
            return "list_item"
        return "paragraph"

    def _join_texts(self, texts: list[str]) -> str:
        return "\n\n".join(texts).strip()

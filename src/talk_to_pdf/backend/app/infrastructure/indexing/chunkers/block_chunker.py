from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

from talk_to_pdf.backend.app.domain.indexing.value_objects import Block, ChunkDraft

FlushReason = Literal["size", "section", "div_end", "end"]


@dataclass(frozen=True, slots=True)
class DefaultBlockChunker:
    """
    Chunk blocks into ChunkDrafts with these rules:

    1) Never cross div boundaries: each chunk belongs to exactly one div_index.
    2) section_head is a hard boundary: it starts a new chunk (no overlap across it).
    3) If content exceeds max_chars, split into multiple chunks.
       On size splits only, prepend overlap_chars from previous chunk text.
    4) Overlap is injected as a synthetic Block(kind="unknown", synthetic=True) so you
       don't need to expand BlockKind; you can ignore synthetic blocks for citations/UI.

    Notes:
    - max_chars and overlap_chars are character-based, not token-based.
    - overlap_chars is capped to avoid pathological behavior when max_chars is small.
    """

    max_chars: int = 1200
    overlap_chars: int = 200

    def chunk(self, *, blocks: list[Block]) -> list[ChunkDraft]:
        prepared = [b for b in blocks if b.text and b.text.strip()]
        if not prepared:
            return []

        # Safety: overlap should never be >= max_chars
        overlap = max(0, min(self.overlap_chars, max(0, self.max_chars // 3)))
        # (cap overlap to at most ~1/3 of max_chars; prevents "all overlap, no progress")

        chunks: list[ChunkDraft] = []

        # Working buffer (within a single div)
        buf_blocks: list[Block] = []
        buf_texts: list[str] = []
        buf_len: int = 0
        chunk_idx: int = 0

        # Track current div
        current_div: int | None = None

        def _block_div_index(b: Block) -> int | None:
            m = b.meta or {}
            v = m.get("div_index")
            return v if isinstance(v, int) else None

        def _is_section_head(b: Block) -> bool:
            return (b.meta or {}).get("kind") == "section_head"

        def _render_block(b: Block) -> str:
            meta = b.meta or {}
            kind = meta.get("kind")
            text = (b.text or "").strip()
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

            # paragraph/reference/footnote/unknown/title -> raw
            return text

        def _join_buf_text() -> str:
            return "\n\n".join(buf_texts).strip()

        def _tail_overlap_text(text: str) -> str:
            if overlap <= 0 or not text:
                return ""
            # Keep tail and normalize whitespace lightly
            tail = text[-overlap:]
            return tail.strip()

        def _make_overlap_block(div_index: int, head_text: str | None, tail_text: str) -> Block:
            # Use kind="unknown" to stay within BlockKind, and mark synthetic=True.
            return Block(
                text=tail_text,
                meta={
                    "div_index": div_index,
                    "head": head_text,
                    "kind": "unknown",
                    "synthetic": True,
                    "synthetic_kind": "overlap_prefix",
                },
            )

        def _current_head_text() -> str | None:
            # Prefer the last seen head in the buffer
            for b in reversed(buf_blocks):
                m = b.meta or {}
                head = m.get("head")
                if isinstance(head, str) and head.strip():
                    return head
            return None

        def _chunk_meta(blocks_in_chunk: list[Block], idx: int, text: str, div_index: int) -> dict[str, Any]:
            # Exclude synthetic overlap blocks from stats
            real_blocks = [b for b in blocks_in_chunk if not (b.meta or {}).get("synthetic")]

            heads = [
                b.meta.get("head")
                for b in real_blocks
                if b.meta and isinstance(b.meta.get("head"), str) and b.meta.get("head")
            ]
            kinds = [b.meta.get("kind", "unknown") for b in real_blocks if b.meta]
            meta: dict[str, Any] = {
                "chunk_index": idx,
                "chunk_char_len": len(text),
                "div_index": div_index,
                "dominant_head": heads[-1] if heads else None,
            }
            if kinds:
                meta["block_counts"] = dict(Counter(kinds))

            # Record overlap presence
            has_overlap = any((b.meta or {}).get("synthetic_kind") == "overlap_prefix" for b in blocks_in_chunk)
            if has_overlap:
                meta["has_overlap_prefix"] = True
                meta["overlap_chars"] = overlap

            return meta

        def flush(reason: FlushReason) -> None:
            nonlocal buf_blocks, buf_texts, buf_len, chunk_idx

            if not buf_blocks:
                return

            # ⛔ DROP header-only chunks
            real_blocks = [
                b for b in buf_blocks
                if not (b.meta or {}).get("synthetic")
            ]

            if (
                    len(real_blocks) == 1
                    and (real_blocks[0].meta or {}).get("kind") == "section_head"
            ):
                # reset buffer and DO NOT emit
                buf_blocks = []
                buf_texts = []
                buf_len = 0
                return

            # Ensure we can compute div_index for meta
            div_index = current_div if current_div is not None else (_block_div_index(buf_blocks[0]) or 0)

            text = _join_buf_text()
            if not text:
                # Nothing meaningful to emit
                buf_blocks = []
                buf_texts = []
                buf_len = 0
                return

            meta = _chunk_meta(buf_blocks, chunk_idx, text, div_index)
            chunks.append(
                ChunkDraft(
                    chunk_index=chunk_idx,
                    blocks=list(buf_blocks),
                    text=text,
                    meta=meta,
                )
            )
            chunk_idx += 1

            # Prepare overlap carry-over only for size splits
            if reason == "size" and overlap > 0:
                tail = _tail_overlap_text(text)
                if tail:
                    head_text = _current_head_text()
                    ov_block = _make_overlap_block(div_index, head_text, tail)
                    ov_rendered = _render_block(ov_block)
                    buf_blocks = [ov_block]
                    buf_texts = [ov_rendered] if ov_rendered else []
                    buf_len = len(ov_rendered)
                    return

            # Otherwise reset fully
            buf_blocks = []
            buf_texts = []
            buf_len = 0

        # Main loop: enforce div boundaries + section boundaries + size splits
        for block in prepared:
            b_div = _block_div_index(block)

            # If div changes, flush and start new div
            if current_div is None:
                current_div = b_div
            elif b_div is not None and current_div is not None and b_div != current_div:
                flush("div_end")
                current_div = b_div

            rendered = _render_block(block)
            if not rendered:
                continue

            # section_head: hard boundary (flush previous) then start with head (no overlap)
            if _is_section_head(block):
                flush("section")
                buf_blocks = [block]
                buf_texts = [rendered]
                buf_len = len(rendered)
                continue

            # Candidate length if we append to current buffer
            sep = 2 if buf_texts else 0  # length of "\n\n"
            candidate_len = buf_len + sep + len(rendered)

            # If it would exceed max_chars, flush due to size (will inject overlap)
            if buf_blocks and candidate_len > self.max_chars:
                flush("size")

            # Append to (possibly reset/overlap-prefixed) buffer
            sep = 2 if buf_texts else 0
            buf_texts.append(rendered)
            buf_blocks.append(block)
            buf_len += sep + len(rendered)

            # Edge case: a single block itself exceeds max_chars.
            # We still emit it as-is (can't split without deeper logic).
            if not buf_blocks:
                buf_blocks = [block]
                buf_texts = [rendered]
                buf_len = len(rendered)

        flush("end")
        return chunks

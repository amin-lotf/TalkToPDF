from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Literal

from talk_to_pdf.backend.app.domain.indexing.value_objects import Block, ChunkDraft

FlushReason = Literal["size", "section", "div_end", "end"]


@dataclass(frozen=True, slots=True)
class DefaultBlockChunker:
    """
    Chunk blocks into ChunkDrafts with:
      - strict max_chars (except truly-unsplittable blocks like huge tables/equations if you choose)
      - div boundary isolation
      - section_head hard boundaries
      - block-based overlap (suffix blocks), not raw char slicing
      - sentence-aware splitting for oversize paragraph-ish blocks

    Key change vs your current implementation:
      - Oversize "paragraph/reference/unknown" blocks are split into multiple synthetic blocks
        BEFORE chunking, so chunk_char_len respects max_chars.
    """

    max_chars: int = 1200
    overlap_chars: int = 200

    # Which kinds are safe to split (intra-block) when they exceed max_chars
    SPLITTABLE_KINDS: tuple[str, ...] = ("paragraph", "reference", "footnote", "unknown")

    def chunk(self, *, blocks: list[Block]) -> list[ChunkDraft]:
        prepared = [b for b in blocks if b.text and b.text.strip()]
        if not prepared:
            return []

        overlap_budget = max(0, min(self.overlap_chars, max(0, self.max_chars // 3)))

        def _block_div_index(b: Block) -> int | None:
            m = b.meta or {}
            v = m.get("div_index")
            return v if isinstance(v, int) else None

        def _kind(b: Block) -> str:
            return (b.meta or {}).get("kind", "unknown")

        def _is_section_head(b: Block) -> bool:
            return _kind(b) == "section_head"

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

            return text

        def _join_texts(texts: list[str]) -> str:
            return "\n\n".join(texts).strip()

        def _current_head_text(buf_blocks: list[Block]) -> str | None:
            for b in reversed(buf_blocks):
                m = b.meta or {}
                head = m.get("head")
                if isinstance(head, str) and head.strip():
                    return head
            return None

        # -------------------------
        # Sentence-aware splitters
        # -------------------------
        _SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")  # sentence-ish boundaries

        def _split_text_sentence_aware(text: str, max_len: int) -> list[tuple[int, int]]:
            """
            Return spans (start,end) that partition text into pieces <= max_len.
            Tries sentence boundaries first; falls back to whitespace; finally hard cut.
            """
            t = text.strip()
            if len(t) <= max_len:
                return [(0, len(t))]

            # Build "chunks" by appending sentences until we reach max_len
            parts = _SENT_SPLIT.split(t)
            spans: list[tuple[int, int]] = []

            # To map back to indices, we walk through the original string.
            # We'll rebuild with a cursor search (safe enough for our use).
            cursor = 0
            cur_start = 0
            cur_len = 0

            def emit(end_pos: int) -> None:
                nonlocal cur_start, cur_len
                if end_pos > cur_start:
                    spans.append((cur_start, end_pos))
                cur_start = end_pos
                cur_len = 0

            for p in parts:
                p = p.strip()
                if not p:
                    continue

                # Find p in t starting from cursor
                idx = t.find(p, cursor)
                if idx == -1:
                    # fallback: if we somehow can't find, treat as hard cut piece
                    idx = cursor

                p_start = idx
                p_end = idx + len(p)
                cursor = p_end

                # If current buffer empty and this sentence alone > max, hard-split it
                if cur_len == 0 and (p_end - cur_start) > max_len:
                    # hard cut the long sentence
                    long_seg = t[cur_start:p_end]
                    i = 0
                    while i < len(long_seg):
                        j = min(i + max_len, len(long_seg))
                        spans.append((cur_start + i, cur_start + j))
                        i = j
                    cur_start = p_end
                    cur_len = 0
                    continue

                # Would adding this sentence exceed max?
                candidate_len = (p_end - cur_start)
                if candidate_len > max_len and cur_len > 0:
                    emit(p_start)
                    # start new with this sentence
                    # (now it should fit unless it's a huge single sentence handled above)
                    cur_len = (p_end - cur_start)
                else:
                    cur_len = candidate_len

            # emit tail
            if cur_start < len(t):
                # if tail still too big, hard split
                tail = t[cur_start:]
                if len(tail) <= max_len:
                    spans.append((cur_start, len(t)))
                else:
                    i = 0
                    while i < len(tail):
                        j = min(i + max_len, len(tail))
                        spans.append((cur_start + i, cur_start + j))
                        i = j

            return spans

        def _split_oversize_blocks(blocks_in: list[Block]) -> list[Block]:
            """
            Preprocess: split oversize splittable blocks into multiple synthetic blocks,
            preserving div_index/head/targets/etc and adding char_start/char_end markers.
            """
            out: list[Block] = []

            for b in blocks_in:
                text = (b.text or "").strip()
                if not text:
                    continue

                k = _kind(b)
                rendered = _render_block(b)

                # Use rendered length to decide oversize for chunking purposes
                if len(rendered) <= self.max_chars:
                    out.append(b)
                    continue

                # Don't split section heads; and only split "paragraph-ish" kinds by default
                if k not in self.SPLITTABLE_KINDS:
                    # keep as-is (will become oversize chunk later)
                    out.append(b)
                    continue

                # Split using ORIGINAL text (not rendered) to keep clean content
                spans = _split_text_sentence_aware(text, self.max_chars)

                # Create synthetic sub-blocks
                base_meta = dict(b.meta or {})
                base_meta["synthetic"] = True
                base_meta["synthetic_kind"] = "split_block"
                base_meta["split_kind"] = k
                base_meta["split_count"] = len(spans)

                for si, (s, e) in enumerate(spans):
                    sub_meta = dict(base_meta)
                    sub_meta["split_index"] = si
                    sub_meta["char_start"] = s
                    sub_meta["char_end"] = e
                    sub_text = text[s:e].strip()
                    out.append(Block(text=sub_text, meta=sub_meta))

            return out

        prepared = _split_oversize_blocks(prepared)

        # -------------------------
        # Chunk assembly
        # -------------------------
        chunks: list[ChunkDraft] = []

        buf_blocks: list[Block] = []
        buf_texts: list[str] = []
        buf_len: int = 0
        chunk_idx: int = 0
        current_div: int | None = None

        def _chunk_meta(blocks_in_chunk: list[Block], idx: int, text: str, div_index: int) -> dict[str, Any]:
            # exclude synthetic overlap blocks from stats; BUT keep split blocks as "real content"
            # (they are synthetic=True, but they are actual content, so treat them as real)
            # We'll only exclude overlap synthetic blocks.
            def is_overlap(b: Block) -> bool:
                return (b.meta or {}).get("synthetic_kind") == "overlap_block"

            real_blocks = [b for b in blocks_in_chunk if not is_overlap(b)]

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

            if any((b.meta or {}).get("synthetic_kind") == "overlap_block" for b in blocks_in_chunk):
                meta["has_overlap_prefix"] = True
                meta["overlap_chars_budget"] = overlap_budget

            return meta

        def _copy_as_overlap_block(b: Block, div_index: int, head_text: str | None) -> Block:
            m = dict(b.meta or {})
            m["div_index"] = div_index
            if head_text is not None:
                m["head"] = head_text
            m["synthetic"] = True
            m["synthetic_kind"] = "overlap_block"
            return Block(text=b.text, meta=m)

        def _carry_overlap_suffix(
            *,
            div_index: int,
            head_text: str | None,
            prev_blocks: list[Block],
            prev_texts: list[str],
        ) -> tuple[list[Block], list[str], int]:
            if overlap_budget <= 0:
                return [], [], 0

            # Prefer overlapping "real content" (exclude overlap blocks; allow split blocks)
            pairs: list[tuple[Block, str]] = []
            for b, t in zip(prev_blocks, prev_texts):
                if (b.meta or {}).get("synthetic_kind") == "overlap_block":
                    continue
                if (b.meta or {}).get("kind") == "section_head":
                    continue
                if t.strip():
                    pairs.append((b, t))

            chosen: list[tuple[Block, str]] = []
            total = 0
            for b, t in reversed(pairs):
                sep = 2 if chosen else 0
                nxt = total + sep + len(t)
                if nxt > overlap_budget:
                    break
                chosen.append((b, t))
                total = nxt
            chosen.reverse()

            if not chosen:
                return [], [], 0

            ov_blocks: list[Block] = []
            ov_texts: list[str] = []
            for b, t in chosen:
                ov_blocks.append(_copy_as_overlap_block(b, div_index, head_text))
                ov_texts.append(t)
            return ov_blocks, ov_texts, total

        def _recompute_buf_len() -> int:
            return len(_join_texts(buf_texts))

        def _ensure_fit_next(rendered_next: str) -> None:
            nonlocal buf_blocks, buf_texts, buf_len

            def cand_len() -> int:
                sep = 2 if buf_texts else 0
                return buf_len + sep + len(rendered_next)

            if cand_len() <= self.max_chars:
                return

            # Drop overlap blocks from the start first
            while buf_blocks and cand_len() > self.max_chars:
                if (buf_blocks[0].meta or {}).get("synthetic_kind") != "overlap_block":
                    break
                buf_blocks.pop(0)
                buf_texts.pop(0)
                buf_len = _recompute_buf_len()

            # If still too big, DO NOT discard. Flush instead.
            if buf_blocks and cand_len() > self.max_chars:
                flush("size")

        def flush(reason: FlushReason) -> None:
            nonlocal buf_blocks, buf_texts, buf_len, chunk_idx

            if not buf_blocks:
                return

            # drop header-only chunks
            real_blocks = [b for b in buf_blocks if (b.meta or {}).get("kind") != "section_head"]
            if not real_blocks:
                buf_blocks = []
                buf_texts = []
                buf_len = 0
                return

            div_index = current_div if current_div is not None else (_block_div_index(buf_blocks[0]) or 0)
            text = _join_texts(buf_texts)
            if not text:
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

            if reason == "size" and overlap_budget > 0:
                head_text = _current_head_text(buf_blocks)
                ov_blocks, ov_texts, ov_len = _carry_overlap_suffix(
                    div_index=div_index,
                    head_text=head_text,
                    prev_blocks=buf_blocks,
                    prev_texts=buf_texts,
                )
                if ov_blocks:
                    buf_blocks = ov_blocks
                    buf_texts = ov_texts
                    buf_len = ov_len
                    return

            buf_blocks = []
            buf_texts = []
            buf_len = 0

        # Main loop: enforce div boundaries + section boundaries + size splits
        for block in prepared:
            b_div = _block_div_index(block)

            if current_div is None:
                current_div = b_div
            elif b_div is not None and current_div is not None and b_div != current_div:
                flush("div_end")
                current_div = b_div

            rendered = _render_block(block)
            if not rendered:
                continue

            # section_head hard boundary
            if _is_section_head(block):
                flush("section")
                buf_blocks = [block]
                buf_texts = [rendered]
                buf_len = len(rendered)
                continue

            # If rendered still exceeds max_chars here, it means it's a non-splittable kind
            # (e.g., huge table/equation). Emit it as its own chunk.
            if len(rendered) > self.max_chars:
                flush("size" if buf_blocks else "end")

                div_index = current_div if current_div is not None else (b_div or 0)
                text = rendered.strip()
                meta = {
                    "chunk_index": chunk_idx,
                    "chunk_char_len": len(text),
                    "div_index": div_index,
                    "dominant_head": (block.meta or {}).get("head"),
                    "block_counts": dict(Counter([_kind(block)])),
                    "oversize_single_block": True,
                    "max_chars": self.max_chars,
                }
                chunks.append(
                    ChunkDraft(
                        chunk_index=chunk_idx,
                        blocks=[block],
                        text=text,
                        meta=meta,
                    )
                )
                chunk_idx += 1
                buf_blocks = []
                buf_texts = []
                buf_len = 0
                continue

            # Ensure buffer + this block fits, dropping overlap if necessary
            _ensure_fit_next(rendered)

            # If still would exceed and we have content, flush size, carry overlap, re-ensure
            sep = 2 if buf_texts else 0
            candidate_len = buf_len + sep + len(rendered)
            if buf_blocks and candidate_len > self.max_chars:
                flush("size")
                _ensure_fit_next(rendered)

            # Append
            sep = 2 if buf_texts else 0
            buf_texts.append(rendered)
            buf_blocks.append(block)
            buf_len += sep + len(rendered)

        flush("end")
        return chunks

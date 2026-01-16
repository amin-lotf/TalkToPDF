from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Protocol

from talk_to_pdf.backend.app.domain.indexing.value_objects import ChunkDraft




_RE_SPACES = re.compile(r"[ \t]+")
_RE_MANY_NEWLINES = re.compile(r"\n{3,}")

# same idea as before (optional). If this causes issues, you can disable it by skipping _split_inline_titles().
_INLINE_TITLE_RE = re.compile(
    r"""
    (?P<prefix>[.!?]["']?\s+)
    (?P<title>
        (?:The|A|An)\s+
        (?:[A-Z][a-z]+|and|or|the|of|to|in|on|at|for|with|from|by)
        (?:\s+(?:[A-Z][a-z]+|and|or|the|of|to|in|on|at|for|with|from|by)){1,9}
    )
    \s+
    (?P<next>[A-Z][a-z]+)\s+(?=[a-z])
    """,
    re.VERBOSE,
)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_inline_titles(text: str) -> str:
    def repl(m: re.Match) -> str:
        title = m.group("title").strip()
        if len(title) > 70 or any(ch in title for ch in [",", ":", ";"]):
            return m.group(0)
        return f"{m.group('prefix')}\n\n{title}\n\n{m.group('next')} "
    return _INLINE_TITLE_RE.sub(repl, text)


def _normalize_text_keep_paragraphs(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_RE_SPACES.sub(" ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = _RE_MANY_NEWLINES.sub("\n\n", text)
    text = text.strip()
    # optional, but helpful for your exact “title glued to sentence” case
    text = _split_inline_titles(text)
    return text.strip()


def _split_paragraphs(text: str) -> list[tuple[int, int, str]]:
    paras: list[tuple[int, int, str]] = []
    n = len(text)
    i = 0
    while i < n:
        while i < n and text[i] == "\n":
            i += 1
        if i >= n:
            break

        start = i
        j = text.find("\n\n", i)
        if j == -1:
            end = n
            p = text[start:end].strip()
            if p:
                paras.append((start, end, p))
            break

        end = j
        p = text[start:end].strip()
        if p:
            paras.append((start, end, p))
        i = j + 2

    return paras


def _is_title_line(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 80:
        return False
    if s.endswith((".", "!", "?", ":", ";", ",")):
        return False
    words = [w for w in re.split(r"\s+", s) if w]
    if len(words) < 2:
        return False
    alpha = [w for w in words if any(c.isalpha() for c in w)]
    if not alpha:
        return False
    tc = sum(1 for w in alpha if w[:1].isupper())
    return tc / len(alpha) >= 0.6


def _paragraph_is_title(paragraph: str) -> bool:
    lines = [ln.strip() for ln in paragraph.split("\n") if ln.strip()]
    return len(lines) == 1 and _is_title_line(lines[0])


def _split_long_block(block: str, max_chars: int) -> list[str]:
    """
    Split a long paragraph/block into <= max_chars pieces.
    Strategy:
    1) sentence-ish split
    2) pack sentences into pieces
    3) fallback: whitespace split if needed
    """
    block = block.strip()
    if not block:
        return []
    if len(block) <= max_chars:
        return [block]

    # 1) try sentence-ish
    sents = [s.strip() for s in _SENT_SPLIT.split(block) if s.strip()]
    if len(sents) <= 1:
        # fallback: whitespace chunk
        return [block[i : i + max_chars].strip() for i in range(0, len(block), max_chars)]

    pieces: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for s in sents:
        add = (1 if cur else 0) + len(s)  # add space if joining
        if cur and cur_len + add > max_chars:
            pieces.append(" ".join(cur).strip())
            cur = [s]
            cur_len = len(s)
        else:
            cur.append(s)
            cur_len += add
    if cur:
        pieces.append(" ".join(cur).strip())

    # hard fallback if any piece still too big (very long sentences)
    final: list[str] = []
    for p in pieces:
        if len(p) <= max_chars:
            final.append(p)
        else:
            final.extend([p[i : i + max_chars].strip() for i in range(0, len(p), max_chars)])
    return [p for p in final if p]


@dataclass(frozen=True, slots=True)
class ParagraphChunker:
    max_chars: int = 1000
    overlap: int = 1
    long_block_overlap_chars: int = 150  # overlap when we split a giant paragraph

    def chunk(self, *, text: str) -> list[ChunkDraft]:
        normalized = _normalize_text_keep_paragraphs(text)
        if not normalized:
            return []

        paras_raw = _split_paragraphs(normalized)
        if not paras_raw:
            return []

        # Expand: if a "paragraph" is huge, split it into smaller pseudo-paragraphs
        paras: list[tuple[int, int, str]] = []
        for p_start, p_end, p_text in paras_raw:
            if len(p_text) <= self.max_chars:
                paras.append((p_start, p_end, p_text))
                continue

            # Split the long paragraph into pieces; we cannot perfectly preserve offsets for each
            # piece unless we compute exact substring positions. We’ll approximate offsets by searching.
            pieces = _split_long_block(p_text, self.max_chars)
            cursor = 0
            for piece in pieces:
                idx = p_text.find(piece, cursor)
                if idx == -1:
                    idx = cursor
                piece_start = p_start + idx
                piece_end = piece_start + len(piece)
                paras.append((piece_start, piece_end, piece))
                cursor = idx + max(1, len(piece) - self.long_block_overlap_chars)

        chunks: list[ChunkDraft] = []
        chunk_idx = 0
        current: list[tuple[int, int, str]] = []
        current_len = 0

        def flush() -> None:
            nonlocal chunk_idx, current, current_len
            if not current:
                return
            chunk_text = "\n\n".join(p[2] for p in current).strip()
            if not chunk_text:
                current = []
                current_len = 0
                return
            char_start = current[0][0]
            char_end = current[-1][1]
            meta = {
                "char_start": char_start,
                "char_end": char_end,
                "chunk_index": chunk_idx,
                "chunk_char_len": len(chunk_text),
            }
            chunks.append(ChunkDraft(chunk_index=chunk_idx, text=chunk_text, meta=meta))
            chunk_idx += 1

            if self.overlap > 0:
                current = current[-self.overlap:]
                current_len = sum(len(p[2]) for p in current) + max(0, 2 * (len(current) - 1))
            else:
                current = []
                current_len = 0

        for p_start, p_end, p_text in paras:
            if _paragraph_is_title(p_text):
                flush()
                meta = {
                    "char_start": p_start,
                    "char_end": p_end,
                    "chunk_index": chunk_idx,
                    "is_title": True,
                    "chunk_char_len": len(p_text.strip()),
                }
                chunks.append(ChunkDraft(chunk_index=chunk_idx, text=p_text.strip(), meta=meta))
                chunk_idx += 1
                current = []
                current_len = 0
                continue

            sep_cost = 2 if current else 0
            projected = current_len + sep_cost + len(p_text)
            if current and projected > self.max_chars:
                flush()

            current.append((p_start, p_end, p_text))
            current_len = sum(len(p[2]) for p in current) + max(0, 2 * (len(current) - 1))

        flush()
        return chunks

from __future__ import annotations

import re

# Existing
_HYPHEN_LINEBREAK = re.compile(r"(?<=\w)-\s*\n\s*(?=\w)")

# NEW: handles "of- floading" / "pri- oritized"
# Example: "of- floading" -> "offloading"
# Only if left side has >=2 letters and right side starts lowercase.
_HYPHEN_SPACE = re.compile(r"(?<=[A-Za-z]{2})-\s+(?=[a-z])")

_SINGLE_NL = re.compile(r"(?<!\n)\n(?!\n)")
_SPACES = re.compile(r"[ \t]{2,}")


def normalize_block_text_by_kind(text: str, kind: str) -> str:
    if kind in ("equation", "table", "code","non-splittable"):
        # Safer: keep structure; only trim and collapse repeated spaces
        t = (text or "").strip()
        t = _SPACES.sub(" ", t)
        return t.strip()
    return normalize_block_text(text)


def normalize_block_text(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""

    # 1) Join hyphenation across explicit line breaks
    t = _HYPHEN_LINEBREAK.sub("", t)

    # 2) Join hyphenation that survived as "- " after newline flattening
    t = _HYPHEN_SPACE.sub("", t)

    # 3) Convert single newlines to spaces (keep paragraph breaks)
    t = _SINGLE_NL.sub(" ", t)

    # 4) Clean up whitespace
    t = _SPACES.sub(" ", t)

    return t.strip()

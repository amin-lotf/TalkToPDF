from __future__ import annotations

import json
from typing import Any

from talk_to_pdf.backend.app.domain.indexing.value_objects import Block


def blocks_to_json(*, blocks: list[Block]) -> str:
    payload = [
        {
            "text": block.text,
            "text_norm": block.text_norm,
            "meta": block.meta or {},
        }
        for block in blocks
    ]
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, default=str)


def render_blocks_markdown(*, provider: str, blocks: list[Block]) -> str:
    lines = [
        "# Extracted Blocks",
        "",
        f"Provider: {provider}",
        f"Total blocks: {len(blocks)}",
        "",
        "---",
    ]

    for index, block in enumerate(blocks, start=1):
        meta: dict[str, Any] = dict(block.meta or {})
        lines.extend(
            [
                "",
                f"## Block {index}",
                "",
                f"**Type:** {meta.get('block_type') or meta.get('kind') or 'unknown'}",
                f"**Pages:** {meta.get('page_start', 'n/a')} - {meta.get('page_end', 'n/a')}",
                f"**Section Path:** {' > '.join(meta.get('section_path') or []) or 'n/a'}",
                "",
                "### Metadata",
                "",
                "```json",
                json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True, default=str),
                "```",
                "",
                "### Text",
                "",
                "~~~text",
                block.text,
                "~~~",
                "",
                "---",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"

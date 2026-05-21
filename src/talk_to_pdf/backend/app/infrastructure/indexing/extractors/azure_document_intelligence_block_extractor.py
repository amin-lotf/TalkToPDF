from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Iterable

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
from azure.core.credentials import AzureKeyCredential

from talk_to_pdf.backend.app.domain.files.interfaces import FileStorage
from talk_to_pdf.backend.app.domain.indexing.value_objects import Block
from talk_to_pdf.backend.app.infrastructure.indexing.text_normalizer import (
    normalize_block_text,
    normalize_block_text_by_kind,
)

_COMMENT_RE = re.compile(
    r'^\s*<!--\s*(?P<kind>PageNumber|PageFooter|PageBreak)(?:="(?P<value>.*?)")?\s*-->\s*$'
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(?P<text>.+?)\s*$")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(?P<text>.+?)\s*$")
_ORDERED_RE = re.compile(r"^\s*(?P<ordinal>\d+)\.\s+(?P<text>.+?)\s*$")
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_DIVIDER_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")


@dataclass(slots=True)
class _AzureMarkdownState:
    physical_page_index: int = 1
    page_labels: list[str] | None = None
    page_footers: list[str] | None = None
    section_path: list[str] | None = None

    def __post_init__(self) -> None:
        if self.page_labels is None:
            self.page_labels = []
        if self.page_footers is None:
            self.page_footers = []
        if self.section_path is None:
            self.section_path = []


def _content_format(value: str) -> DocumentContentFormat:
    if value == "markdown":
        return DocumentContentFormat.MARKDOWN
    return DocumentContentFormat.TEXT


def _is_comment(line: str) -> bool:
    return bool(_COMMENT_RE.match(line))


def _is_heading(line: str) -> bool:
    return bool(_HEADING_RE.match(line.strip()))


def _is_list_item(line: str) -> bool:
    stripped = line.strip()
    return bool(_BULLET_RE.match(stripped) or _ORDERED_RE.match(stripped))


def _is_table_line(line: str) -> bool:
    stripped = line.rstrip()
    return bool(_TABLE_RE.match(stripped) or _TABLE_DIVIDER_RE.match(stripped))


def _parse_comment(line: str, state: _AzureMarkdownState) -> None:
    match = _COMMENT_RE.match(line)
    if not match:
        return

    kind = match.group("kind")
    value = match.group("value")
    if kind == "PageNumber":
        if value:
            state.page_labels.append(value.strip())
        return

    if kind == "PageFooter":
        if value:
            state.page_footers.append(value.strip())
        return

def _apply_page_segment_meta(
    *,
    blocks: list[Block],
    start_index: int,
    state: _AzureMarkdownState,
) -> None:
    segment_blocks = blocks[start_index:]
    if not segment_blocks:
        return

    page_labels = [label for label in state.page_labels or [] if label]
    page_footers = [footer for footer in state.page_footers or [] if footer]

    unique_page_labels = list(dict.fromkeys(page_labels))
    unique_page_footers = list(dict.fromkeys(page_footers))

    for offset, block in enumerate(segment_blocks):
        meta = dict(block.meta or {})
        if unique_page_labels:
            meta["page_labels"] = list(unique_page_labels)
            if len(unique_page_labels) == 1:
                meta["page_label"] = unique_page_labels[0]
        if unique_page_footers:
            meta["page_footers"] = list(unique_page_footers)
            if len(unique_page_footers) == 1:
                meta["page_footer"] = unique_page_footers[0]
        blocks[start_index + offset] = Block(
            text=block.text,
            text_norm=block.text_norm,
            meta=meta,
        )


def _section_path_for_heading(*, current: list[str], level: int, heading: str) -> list[str]:
    next_path = list(current[: max(0, level - 1)])
    next_path.append(heading)
    return next_path


def _base_meta(*, state: _AzureMarkdownState, block_type: str, kind: str) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "provider": "azure_document_intelligence",
        "block_type": block_type,
        "kind": kind,
        "section_path": list(state.section_path or []),
        "page_start": state.physical_page_index,
        "page_end": state.physical_page_index,
    }
    return meta


def _paragraph_text(lines: Iterable[str]) -> str:
    return normalize_block_text("\n".join(line.rstrip() for line in lines))


def _table_text(lines: Iterable[str]) -> str:
    return "\n".join(line.rstrip() for line in lines).strip()


def parse_azure_document_markdown(*, markdown: str) -> list[Block]:
    lines = markdown.splitlines()
    blocks: list[Block] = []
    state = _AzureMarkdownState()
    current_page_block_start = 0

    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        text = _paragraph_text(paragraph_lines)
        paragraph_lines = []
        if not text:
            return

        meta = _base_meta(state=state, block_type="paragraph", kind="paragraph")
        blocks.append(
            Block(
                text=text,
                text_norm=normalize_block_text_by_kind(text, kind="paragraph"),
                meta=meta,
            )
        )

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if _is_comment(stripped):
            flush_paragraph()
            match = _COMMENT_RE.match(stripped)
            if match and match.group("kind") == "PageBreak":
                _apply_page_segment_meta(
                    blocks=blocks,
                    start_index=current_page_block_start,
                    state=state,
                )
                state.physical_page_index += 1
                state.page_labels = []
                state.page_footers = []
                current_page_block_start = len(blocks)
                index += 1
                continue
            _parse_comment(stripped, state)
            index += 1
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            flush_paragraph()
            heading_text = normalize_block_text(heading_match.group("text"))
            heading_level = len(heading_match.group(1))
            state.section_path = _section_path_for_heading(
                current=list(state.section_path or []),
                level=heading_level,
                heading=heading_text,
            )
            meta = _base_meta(state=state, block_type="heading", kind="section_head")
            meta["heading_level"] = heading_level
            blocks.append(
                Block(
                    text=heading_text,
                    text_norm=normalize_block_text_by_kind(heading_text, kind="section_head"),
                    meta=meta,
                )
            )
            index += 1
            continue

        if _is_table_line(line):
            flush_paragraph()
            table_lines: list[str] = []
            while index < len(lines):
                current = lines[index]
                current_stripped = current.strip()
                if not current_stripped:
                    break
                if _is_comment(current_stripped) or _is_heading(current_stripped):
                    break
                if not _is_table_line(current):
                    break
                table_lines.append(current)
                index += 1

            table_text = _table_text(table_lines)
            if table_text:
                meta = _base_meta(state=state, block_type="table", kind="table")
                blocks.append(
                    Block(
                        text=table_text,
                        text_norm=normalize_block_text_by_kind(table_text, kind="table"),
                        meta=meta,
                    )
                )
            continue

        if _is_list_item(line):
            flush_paragraph()
            while index < len(lines):
                current = lines[index]
                current_stripped = current.strip()
                if not current_stripped:
                    break
                if _is_comment(current_stripped) or _is_heading(current_stripped) or _is_table_line(current):
                    break

                bullet_match = _BULLET_RE.match(current_stripped)
                ordered_match = _ORDERED_RE.match(current_stripped)
                if not bullet_match and not ordered_match:
                    break

                item_lines = [
                    bullet_match.group("text") if bullet_match else ordered_match.group("text")
                ]
                ordinal = int(ordered_match.group("ordinal")) if ordered_match else None
                list_kind = "ordered" if ordered_match else "bullet"
                index += 1

                while index < len(lines):
                    continuation = lines[index]
                    continuation_stripped = continuation.strip()
                    if not continuation_stripped:
                        break
                    if (
                        _is_comment(continuation_stripped)
                        or _is_heading(continuation_stripped)
                        or _is_table_line(continuation)
                        or _is_list_item(continuation)
                    ):
                        break
                    item_lines.append(continuation_stripped)
                    index += 1

                item_text = _paragraph_text(item_lines)
                if item_text:
                    meta = _base_meta(state=state, block_type="list_item", kind="list_item")
                    meta["list_kind"] = list_kind
                    if ordinal is not None:
                        meta["list_ordinal"] = ordinal
                    blocks.append(
                        Block(
                            text=item_text,
                            text_norm=normalize_block_text_by_kind(item_text, kind="list_item"),
                            meta=meta,
                        )
                    )

                if index >= len(lines):
                    break
                next_stripped = lines[index].strip()
                if not next_stripped or _is_comment(next_stripped) or _is_heading(next_stripped) or _is_table_line(lines[index]):
                    break
                if not _is_list_item(lines[index]):
                    break
            continue

        paragraph_lines.append(line)
        index += 1

    flush_paragraph()
    _apply_page_segment_meta(
        blocks=blocks,
        start_index=current_page_block_start,
        state=state,
    )
    return [block for block in blocks if block.text.strip()]


class AzureDocumentIntelligenceBlockExtractor:
    def __init__(
        self,
        *,
        file_storage: FileStorage,
        endpoint: str,
        api_key: str,
        model_id: str = "prebuilt-layout",
        output_format: str = "markdown",
        client: DocumentIntelligenceClient | None = None,
    ) -> None:
        if not endpoint:
            raise ValueError("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT must be provided")
        if not api_key:
            raise ValueError("AZURE_DOCUMENT_INTELLIGENCE_KEY must be provided")
        if not model_id:
            raise ValueError("AZURE_DOCUMENT_INTELLIGENCE_MODEL must be provided")

        self._file_storage = file_storage
        self._model_id = model_id
        self._output_format = output_format
        self._client = client or DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key),
        )

    async def extract(self, *, storage_path: str) -> list[Block]:
        try:
            pdf_bytes = await self._file_storage.read_bytes(storage_path=storage_path)
        except Exception as e:
            raise RuntimeError("Failed to read PDF file") from e

        try:
            markdown = await asyncio.to_thread(self._analyze_to_markdown, pdf_bytes)
        except Exception as e:
            raise RuntimeError("Azure Document Intelligence extraction failed") from e

        blocks = parse_azure_document_markdown(markdown=markdown)
        if not blocks and markdown.strip():
            raise RuntimeError("Azure Document Intelligence returned content but no parseable blocks")
        return blocks

    def _analyze_to_markdown(self, pdf_bytes: bytes) -> str:
        poller = self._client.begin_analyze_document(
            self._model_id,
            AnalyzeDocumentRequest(bytes_source=pdf_bytes),
            output_content_format=_content_format(self._output_format),
        )
        result = poller.result()
        content = getattr(result, "content", None)
        if not isinstance(content, str):
            raise RuntimeError("Azure Document Intelligence result content is missing")
        return content

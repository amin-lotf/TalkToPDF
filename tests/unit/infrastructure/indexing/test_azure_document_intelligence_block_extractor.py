from __future__ import annotations

from types import SimpleNamespace

import pytest
from azure.ai.documentintelligence.models import DocumentContentFormat

from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.azure_markdown_block_chunker import (
    AzureMarkdownBlockChunker,
)
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.azure_document_intelligence_block_extractor import (
    AzureDocumentIntelligenceBlockExtractor,
    parse_azure_document_markdown,
)
from tests.unit.fakes.project_storage import FakeFileStorage

MARKDOWN_SAMPLE = """
<!-- PageNumber="6" -->
<!-- PageFooter="BMW GROUP CODE ON HUMAN RIGHTS AND WORKING CONDITIONS" -->
# 1. INTRODUCTION
## 1.1. BASICS
Responsible, sustainable, and lawful conduct in the environ-
mental domain matters.

- First bullet wraps
  across lines
- Second bullet

| Topic | Owner |
| --- | --- |
| Human rights | Board |

<!-- PageBreak -->
<!-- PageNumber="7" -->
### In addition to locally applicable legal requirements...
This section continues here.
""".strip()


class FakePoller:
    def __init__(self, content: str) -> None:
        self._content = content

    def result(self):
        return SimpleNamespace(content=self._content)


class FakeAzureDocumentIntelligenceClient:
    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: list[dict] = []

    def begin_analyze_document(self, model_id, body, **kwargs):
        self.calls.append(
            {
                "model_id": model_id,
                "body": body,
                **kwargs,
            }
        )
        return FakePoller(self._content)


@pytest.mark.asyncio
async def test_azure_document_intelligence_extractor_parses_markdown_blocks():
    file_storage = FakeFileStorage()
    file_storage._files["docs/sample.pdf"] = b"%PDF-1.7 test"
    client = FakeAzureDocumentIntelligenceClient(MARKDOWN_SAMPLE)
    extractor = AzureDocumentIntelligenceBlockExtractor(
        file_storage=file_storage,
        endpoint="https://example.cognitiveservices.azure.com/",
        api_key="test-key",
        client=client,
    )

    blocks = await extractor.extract(storage_path="docs/sample.pdf")

    assert client.calls
    assert client.calls[0]["model_id"] == "prebuilt-layout"
    assert client.calls[0]["output_content_format"] == DocumentContentFormat.MARKDOWN

    heading_blocks = [block for block in blocks if (block.meta or {}).get("block_type") == "heading"]
    assert [block.meta.get("heading_level") for block in heading_blocks] == [1, 2, 3]

    subsection_heading = heading_blocks[1]
    assert subsection_heading.text == "1.1. BASICS"
    assert subsection_heading.meta["section_path"] == ["1. INTRODUCTION", "1.1. BASICS"]
    assert subsection_heading.meta["page_start"] == 6
    assert subsection_heading.meta["page_end"] == 6

    paragraph = next(block for block in blocks if (block.meta or {}).get("block_type") == "paragraph")
    assert paragraph.text == "Responsible, sustainable, and lawful conduct in the environmental domain matters."
    assert paragraph.meta["section_path"] == ["1. INTRODUCTION", "1.1. BASICS"]
    assert paragraph.meta["page_start"] == 6
    assert paragraph.meta["page_end"] == 6
    assert paragraph.meta["page_footer"] == "BMW GROUP CODE ON HUMAN RIGHTS AND WORKING CONDITIONS"

    list_blocks = [block for block in blocks if (block.meta or {}).get("block_type") == "list_item"]
    assert len(list_blocks) == 2
    assert list_blocks[0].text == "First bullet wraps across lines"
    assert list_blocks[0].meta["section_path"] == ["1. INTRODUCTION", "1.1. BASICS"]

    table_block = next(block for block in blocks if (block.meta or {}).get("block_type") == "table")
    assert table_block.meta["page_start"] == 6
    assert table_block.meta["page_end"] == 6
    assert "| Topic | Owner |" in table_block.text

    assert all("BMW GROUP CODE ON HUMAN RIGHTS AND WORKING CONDITIONS" != block.text for block in blocks)


def test_azure_markdown_block_chunker_preserves_section_and_page_metadata():
    blocks = parse_azure_document_markdown(markdown=MARKDOWN_SAMPLE)
    chunker = AzureMarkdownBlockChunker(max_chars=120, overlap_chars=20)

    chunks = chunker.chunk(blocks=blocks)

    assert len(chunks) >= 3

    first = chunks[0]
    assert first.meta["section_path"] == ["1. INTRODUCTION", "1.1. BASICS"]
    assert first.meta["page_start"] == 6
    assert first.meta["page_end"] == 6
    assert "Responsible, sustainable, and lawful conduct" in first.text

    table_chunk = next(chunk for chunk in chunks if "| Topic | Owner |" in chunk.text)
    assert table_chunk.meta["section_path"] == ["1. INTRODUCTION", "1.1. BASICS"]
    assert table_chunk.meta["page_start"] == 6
    assert table_chunk.meta["page_end"] == 6
    assert table_chunk.meta["block_counts"]["table"] == 1

    final = chunks[-1]
    assert final.meta["section_path"] == [
        "1. INTRODUCTION",
        "1.1. BASICS",
        "In addition to locally applicable legal requirements...",
    ]
    assert final.meta["page_start"] == 7
    assert final.meta["page_end"] == 7
    assert "This section continues here." in final.text

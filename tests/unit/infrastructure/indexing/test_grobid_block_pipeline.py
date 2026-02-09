from __future__ import annotations

import pytest

from talk_to_pdf.backend.app.domain.indexing.value_objects import Block
from talk_to_pdf.backend.app.infrastructure.indexing.chunkers.block_chunker import DefaultBlockChunker
from talk_to_pdf.backend.app.infrastructure.indexing.extractors.grobid_tei_block_extractor import (
    GrobidTeiBlockExtractor,
)
from talk_to_pdf.backend.app.infrastructure.indexing.text_normalizer import normalize_block_text_by_kind

TEI_SAMPLE = """
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text>
    <body>
      <div xml:id="d1">
        <head>Introduction</head>
        <p>First paragraph with <ref target="#b1">ref</ref>.</p>
        <formula xml:id="eq1"><label>1</label>E = mc^2</formula>
      </div>
      <div type="references">
        <head>References</head>
        <listBibl>
          <bibl xml:id="b1"><title>Reference One</title></bibl>
        </listBibl>
      </div>
    </body>
  </text>
</TEI>
"""


def test_grobid_block_extractor_handles_refs_and_equations():
    extractor = GrobidTeiBlockExtractor()

    blocks = extractor.extract(xml=TEI_SAMPLE)

    kinds = [b.meta.get("kind") for b in blocks if b.meta]
    assert "section_head" in kinds
    assert "paragraph" in kinds
    assert "equation" in kinds
    assert "reference" in kinds

    para = next(b for b in blocks if b.meta and b.meta.get("kind") == "paragraph")
    assert para.meta.get("targets") == ["#b1"]

    eq = next(b for b in blocks if b.meta and b.meta.get("kind") == "equation")
    assert eq.meta.get("equation_label") == "1"


def test_default_block_chunker_groups_heads_and_paragraphs():
    blocks = [
        Block(
            text="Intro",
            text_norm= normalize_block_text_by_kind(text="Intro", kind="section_head"),
            meta={"kind": "section_head", "div_index": 0, "head": "Intro", "xml_id": "h1", "targets": []},
        ),
        Block(
            text="First paragraph text under intro section.",
            text_norm= normalize_block_text_by_kind(text="First paragraph text under intro section.", kind="paragraph"),
            meta={"kind": "paragraph", "div_index": 0, "head": "Intro", "xml_id": "p1", "targets": []},
        ),
        Block(
            text="Second paragraph text that should spill into the next chunk when combined.",
            text_norm= normalize_block_text_by_kind(text="Second paragraph text that should spill into the next chunk when combined.", kind="paragraph"),
            meta={"kind": "paragraph", "div_index": 1, "head": "Body", "xml_id": "p2", "targets": []},
        ),
        Block(
            text="E = mc^2",
            text_norm= normalize_block_text_by_kind(text="E = mc^2", kind="equation"),
            meta={
                "kind": "equation",
                "div_index": 1,
                "head": "Body",
                "xml_id": "eq1",
                "equation_label": "(1)",
                "targets": [],
            },
        ),
    ]

    chunker = DefaultBlockChunker(max_chars=60)

    chunks = chunker.chunk(blocks=blocks)

    assert len(chunks) == 3

    first = chunks[0]
    assert first.text.startswith("## Intro")
    assert "First paragraph" in first.text
    assert first.meta.get("dominant_head") == "Intro"
    assert first.meta.get("div_index") == 0
    assert first.meta.get("block_counts", {}).get("section_head") == 1

    middle = chunks[1]
    assert middle.meta.get("div_index") == 1
    assert middle.meta.get("chunk_char_len") <= 60
    assert middle.blocks[0].meta.get("synthetic_kind") == "split_block"
    assert middle.meta.get("block_counts", {}).get("paragraph") == 1

    tail = chunks[2]
    assert tail.meta.get("div_index") == 1
    assert tail.blocks[0].meta.get("synthetic_kind") == "split_block"
    assert "(1)" in tail.text
    assert "E = mc^2" in tail.text
    assert tail.meta.get("block_counts", {}).get("equation") == 1

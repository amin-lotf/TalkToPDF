from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree as ET

from talk_to_pdf.backend.app.domain.indexing.value_objects import Block, BlockKind

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
XML_ID_ATTR = "{http://www.w3.org/XML/1998/namespace}id"
_WS = re.compile(r"\s+")


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return _WS.sub(" ", text).strip()


def _strip_tag(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _get_xml_id(elem: ET.Element | None) -> str | None:
    if elem is None:
        return None
    return elem.attrib.get(XML_ID_ATTR) or elem.attrib.get("xml:id") or elem.attrib.get("id")


def _text_and_targets(elem: ET.Element) -> tuple[str, list[str]]:
    """
    Flatten element text while preserving inline ref text and collecting @target values.
    """
    parts: list[str] = []
    targets: list[str] = []

    def walk(node: ET.Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in list(node):
            if _strip_tag(child.tag) == "ref":
                if child.text:
                    parts.append(child.text)
                target = child.attrib.get("target")
                if target:
                    targets.append(target)
                walk(child)
                if child.tail:
                    parts.append(child.tail)
            else:
                walk(child)
                if child.tail:
                    parts.append(child.tail)

    walk(elem)
    return _normalize_text("".join(parts)), targets


class GrobidTeiBlockExtractor:
    """
    Parse GROBID TEI XML into semantic blocks.
    """

    def extract(self, *, xml: str) -> list[Block]:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as e:
            raise ValueError("Invalid TEI XML") from e

        body = root.find(".//tei:text/tei:body", TEI_NS)
        if body is None:
            return []

        blocks: list[Block] = []
        for div_index, div in enumerate(body.iterfind(".//tei:div", TEI_NS)):
            blocks.extend(self._extract_div(div=div, div_index=div_index))
        return [b for b in blocks if b.text]

    def _extract_div(self, *, div: ET.Element, div_index: int) -> list[Block]:
        out: list[Block] = []
        head_el = div.find("tei:head", TEI_NS)
        head_text = _normalize_text("".join(head_el.itertext())) if head_el is not None else None
        ref_section = self._is_reference_div(div, head_text)

        if head_text:
            out.append(
                Block(
                    text=head_text,
                    meta={
                        "div_index": div_index,
                        "head": head_text,
                        "kind": "section_head",
                        "xml_id": _get_xml_id(head_el) or _get_xml_id(div),
                        "targets": [],
                    },
                )
            )

        for child in list(div):
            tag = _strip_tag(child.tag)
            if tag == "head":
                continue
            if tag == "p":
                blk = self._paragraph_block(child, div_index, head_text, ref_section)
                if blk:
                    out.append(blk)
            elif tag in {"formula", "equation"}:
                blk = self._equation_block(child, div_index, head_text)
                if blk:
                    out.append(blk)
            elif tag == "table":
                blk = self._simple_block(child, div_index, head_text, kind="table")
                if blk:
                    out.append(blk)
            elif tag == "figure":
                blk = self._figure_block(child, div_index, head_text)
                if blk:
                    out.append(blk)
            elif tag == "list":
                out.extend(self._list_blocks(child, div_index, head_text, ref_section))
            elif tag == "note":
                blk = self._note_block(child, div_index, head_text)
                if blk:
                    out.append(blk)
            elif tag in {"ref", "ptr", "bibl", "biblStruct", "listBibl"}:
                blk = self._simple_block(child, div_index, head_text, kind="reference")
                if blk:
                    out.append(blk)
            else:
                fallback = _normalize_text("".join(child.itertext()))
                if fallback:
                    out.append(
                        Block(
                            text=fallback,
                            meta={
                                "div_index": div_index,
                                "head": head_text,
                                "kind": "unknown",
                                "xml_id": _get_xml_id(child),
                                "targets": [],
                            },
                        )
                    )
        return out

    def _paragraph_block(
        self,
        elem: ET.Element,
        div_index: int,
        head_text: str | None,
        is_reference: bool,
    ) -> Block | None:
        text, targets = _text_and_targets(elem)
        if not text:
            return None
        kind: BlockKind = "reference" if is_reference else "paragraph"
        meta: dict[str, Any] = {
            "div_index": div_index,
            "head": head_text,
            "kind": kind,
            "xml_id": _get_xml_id(elem),
            "targets": targets,
        }
        return Block(text=text, meta=meta)

    def _equation_block(self, elem: ET.Element, div_index: int, head_text: str | None) -> Block | None:
        label_el = elem.find("tei:label", TEI_NS)
        label = _normalize_text(label_el.text) if label_el is not None else None
        label = label or elem.attrib.get("n")

        body_parts: list[str] = []
        for child in list(elem):
            if child is label_el:
                continue
            body_parts.append("".join(child.itertext()))
        eq_text = _normalize_text(" ".join(body_parts) or "".join(elem.itertext()))
        if not eq_text and not label:
            return None

        return Block(
            text=eq_text or (label or ""),
            meta={
                "div_index": div_index,
                "head": head_text,
                "kind": "equation",
                "xml_id": _get_xml_id(elem),
                "equation_label": label,
                "targets": [],
            },
        )

    def _simple_block(
        self,
        elem: ET.Element,
        div_index: int,
        head_text: str | None,
        *,
        kind: BlockKind,
    ) -> Block | None:
        text = _normalize_text("".join(elem.itertext()))
        if not text:
            return None
        meta = {
            "div_index": div_index,
            "head": head_text,
            "kind": kind,
            "xml_id": _get_xml_id(elem),
            "targets": [],
        }
        return Block(text=text, meta=meta)

    def _figure_block(self, elem: ET.Element, div_index: int, head_text: str | None) -> Block | None:
        desc = elem.find("tei:figDesc", TEI_NS)
        text = _normalize_text("".join(desc.itertext())) if desc is not None else _normalize_text("".join(elem.itertext()))
        if not text:
            return None
        return Block(
            text=text,
            meta={
                "div_index": div_index,
                "head": head_text,
                "kind": "figure_caption",
                "xml_id": _get_xml_id(elem),
                "targets": [],
            },
        )

    def _list_blocks(
        self,
        elem: ET.Element,
        div_index: int,
        head_text: str | None,
        is_reference: bool,
    ) -> list[Block]:
        items: list[Block] = []
        for item in elem.findall("tei:item", TEI_NS):
            text, targets = _text_and_targets(item)
            if not text:
                continue
            meta = {
                "div_index": div_index,
                "head": head_text,
                "kind": "list_item" if not is_reference else "reference",
                "xml_id": _get_xml_id(item),
                "targets": targets,
            }
            items.append(Block(text=text, meta=meta))
        return items

    def _note_block(self, elem: ET.Element, div_index: int, head_text: str | None) -> Block | None:
        text, targets = _text_and_targets(elem)
        if not text:
            return None
        place = (elem.attrib.get("place") or "").lower()
        note_type = (elem.attrib.get("type") or "").lower()
        kind: BlockKind = "footnote" if ("foot" in place or "foot" in note_type) else "unknown"
        meta = {
            "div_index": div_index,
            "head": head_text,
            "kind": kind,
            "xml_id": _get_xml_id(elem),
            "targets": targets,
        }
        return Block(text=text, meta=meta)

    def _is_reference_div(self, div: ET.Element, head_text: str | None) -> bool:
        dtype = (div.attrib.get("type") or "").lower()
        if "reference" in dtype or "bibl" in dtype:
            return True
        if head_text and "reference" in head_text.lower():
            return True
        return False


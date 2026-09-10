#!/usr/bin/env python3
"""Convert the reports produced by this Skill from Markdown to DOCX.

The converter deliberately implements the small Markdown subset used by the
templates instead of depending on a renderer with an unstable extension set.
It supports headings, lists, block quotes, fenced and inline code, links,
tables, and real Word footnotes. A final internal annotation section can be
converted to Word comments by the bundled companion script.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape as xml_escape

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from lxml import etree


CN_FONT = "宋体"
HEADING_FONT = "黑体"
CODE_FONT = "Courier New"
HYPERLINK_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
FOOTNOTE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes"
FOOTNOTE_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"
FOOTNOTE_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

FOOTNOTE_DEF_RE = re.compile(r"^[ \t]*\[\^([^\]\s]+)\]:[ \t]*(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
UNORDERED_LIST_RE = re.compile(r"^[-*+][ \t]+(.*)$")
ORDERED_LIST_RE = re.compile(r"^\d+[.)][ \t]+(.*)$")
FONT_TAG_RE = re.compile(
    r'<font\s+color\s*=\s*["\']([^"\']+)["\']\s*>(.*?)</font>',
    re.IGNORECASE | re.DOTALL,
)
SPAN_TAG_RE = re.compile(
    r'<span\s+style\s*=\s*["\']([^"\']*)["\']\s*>(.*?)</span>',
    re.IGNORECASE | re.DOTALL,
)
COLOR_RE = re.compile(r"^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
RAW_URL_RE = re.compile(r"(?:https?://|mailto:)", re.IGNORECASE)


@dataclass(frozen=True)
class InlineToken:
    kind: str
    text: str
    target: str | None = None
    color: str | None = None
    bold: bool = False


@dataclass
class ConversionContext:
    footnote_definitions: dict[str, str]
    footnote_ids: dict[str, int]


def _set_run_font(
    run,
    *,
    font_name: str = CN_FONT,
    size: float | None = None,
    bold: bool | None = None,
    color: str | None = None,
) -> None:
    """Set both Western and East Asian fonts on a python-docx run."""
    run.font.name = font_name
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), font_name)
    rfonts.set(qn("w:ascii"), font_name)
    rfonts.set(qn("w:hAnsi"), font_name)
    if color and COLOR_RE.fullmatch(color.strip()):
        normalized = color.strip().lstrip("#")
        if len(normalized) == 3:
            normalized = "".join(ch * 2 for ch in normalized)
        run.font.color.rgb = RGBColor.from_string(normalized.upper())


def _append_text(paragraph, text: str, *, bold: bool = False, code: bool = False, color: str | None = None) -> None:
    """Append text while retaining explicit line breaks in Markdown content."""
    parts = text.split("\n")
    for index, part in enumerate(parts):
        if part:
            run = paragraph.add_run(part)
            _set_run_font(
                run,
                font_name=CODE_FONT if code else CN_FONT,
                size=9.5 if code else None,
                bold=bold,
                color=color,
            )
        if index < len(parts) - 1:
            break_run = paragraph.add_run()
            _set_run_font(break_run, font_name=CODE_FONT if code else CN_FONT, size=9.5 if code else None)
            break_run.add_break()


def _add_hyperlink(paragraph, url: str, text: str) -> None:
    """Add an external hyperlink, including relative and mailto targets."""
    relationship_id = paragraph.part.relate_to(url, HYPERLINK_REL, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    rpr.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rpr.append(underline)
    rfonts = OxmlElement("w:rFonts")
    rfonts.set(qn("w:eastAsia"), CN_FONT)
    rfonts.set(qn("w:ascii"), CN_FONT)
    rfonts.set(qn("w:hAnsi"), CN_FONT)
    rpr.append(rfonts)
    run.append(rpr)
    for index, part in enumerate(text.split("\n")):
        if part:
            node = OxmlElement("w:t")
            if part[:1].isspace() or part[-1:].isspace():
                node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            node.text = part
            run.append(node)
        if index < len(text.split("\n")) - 1:
            run.append(OxmlElement("w:br"))
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def _parse_markdown_link(text: str, start: int) -> tuple[str, str, int] | None:
    """Return label, target, and the index after a balanced Markdown link."""
    closing_label = text.find("](", start + 1)
    if closing_label < 0:
        return None
    label = text[start + 1 : closing_label]
    cursor = closing_label + 2
    depth = 0
    while cursor < len(text):
        char = text[cursor]
        if char == "\\" and cursor + 1 < len(text):
            cursor += 2
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                target = text[closing_label + 2 : cursor].strip()
                if target:
                    return label, target, cursor + 1
                return None
            depth -= 1
        cursor += 1
    return None


def _consume_bare_url(text: str, start: int) -> tuple[str, int] | None:
    match = RAW_URL_RE.match(text, start)
    if not match:
        return None
    cursor = start
    while cursor < len(text) and not text[cursor].isspace() and text[cursor] not in '<>"\'':
        cursor += 1
    candidate = text[start:cursor]
    while candidate and candidate[-1] in ".,;:!?。，；：！？":
        candidate = candidate[:-1]
        cursor -= 1
    pairs = ((")", "("), ("]", "["), ("}", "{"))
    changed = True
    while candidate and changed:
        changed = False
        for closing, opening in pairs:
            if candidate.endswith(closing) and candidate.count(closing) > candidate.count(opening):
                candidate = candidate[:-1]
                cursor -= 1
                changed = True
    return (candidate, cursor) if candidate else None


def _tokenize_inline(text: str, *, include_footnotes: bool = True) -> list[InlineToken]:
    """Parse the intentionally small inline Markdown dialect used by reports."""
    tokens: list[InlineToken] = []
    plain: list[str] = []

    def flush_plain() -> None:
        if plain:
            tokens.append(InlineToken("text", "".join(plain)))
            plain.clear()

    index = 0
    while index < len(text):
        if text[index] == "\\" and index + 1 < len(text) and text[index + 1] in "\\|`*[]()":
            plain.append(text[index + 1])
            index += 2
            continue

        if text.startswith("**", index):
            end = text.find("**", index + 2)
            if end >= 0:
                flush_plain()
                tokens.append(InlineToken("bold", text[index + 2 : end], bold=True))
                index = end + 2
                continue

        if text[index] == "`":
            tick_count = 1
            while index + tick_count < len(text) and text[index + tick_count] == "`":
                tick_count += 1
            marker = "`" * tick_count
            end = text.find(marker, index + tick_count)
            if end >= 0:
                flush_plain()
                tokens.append(InlineToken("code", text[index + tick_count : end]))
                index = end + tick_count
                continue

        if include_footnotes and text.startswith("[^", index):
            end = text.find("]", index + 2)
            if end >= 0:
                label = text[index + 2 : end]
                if label and "[" not in label:
                    flush_plain()
                    tokens.append(InlineToken("footnote", label))
                    index = end + 1
                    continue

        if text[index] == "[":
            link = _parse_markdown_link(text, index)
            if link is not None:
                label, target, end = link
                flush_plain()
                tokens.append(InlineToken("link", label, target=target))
                index = end
                continue

        font_match = FONT_TAG_RE.match(text, index)
        if font_match is not None:
            flush_plain()
            color = font_match.group(1) if COLOR_RE.fullmatch(font_match.group(1).strip()) else None
            tokens.append(InlineToken("styled", font_match.group(2), color=color))
            index = font_match.end()
            continue

        span_match = SPAN_TAG_RE.match(text, index)
        if span_match is not None:
            flush_plain()
            style = span_match.group(1)
            color_match = re.search(r"(?:^|;)\s*color\s*:\s*([^;\s]+)", style, re.IGNORECASE)
            color = color_match.group(1) if color_match and COLOR_RE.fullmatch(color_match.group(1)) else None
            bold = bool(re.search(r"font-weight\s*:\s*(?:bold|[6-9]00)", style, re.IGNORECASE))
            tokens.append(InlineToken("styled", span_match.group(2), color=color, bold=bold))
            index = span_match.end()
            continue

        url = _consume_bare_url(text, index)
        if url is not None:
            target, end = url
            flush_plain()
            tokens.append(InlineToken("link", target, target=target))
            index = end
            continue

        plain.append(text[index])
        index += 1

    flush_plain()
    return tokens


def _footnote_labels_in_line(line: str) -> Iterable[str]:
    """Find references outside inline-code spans so code examples remain literal."""
    index = 0
    marker: str | None = None
    while index < len(line):
        if line[index] == "`":
            count = 1
            while index + count < len(line) and line[index + count] == "`":
                count += 1
            ticks = "`" * count
            if marker is None:
                marker = ticks
            elif marker == ticks:
                marker = None
            index += count
            continue
        if marker is None and line.startswith("[^", index):
            end = line.find("]", index + 2)
            if end >= 0:
                label = line[index + 2 : end]
                if label and "[" not in label:
                    yield label
                    index = end + 1
                    continue
        index += 1


def _collect_footnotes(lines: list[str]) -> tuple[dict[str, str], set[int], dict[str, int]]:
    """Collect definitions, continuation lines, and referenced labels before rendering."""
    definitions: dict[str, str] = {}
    skipped_lines: set[int] = set()
    index = 0
    active_fence: str | None = None
    while index < len(lines):
        fence = FENCE_RE.match(lines[index])
        if fence:
            marker = fence.group(1)
            if active_fence is None:
                active_fence = marker
            elif marker[0] == active_fence[0] and len(marker) >= len(active_fence):
                active_fence = None
            index += 1
            continue
        if active_fence is not None:
            index += 1
            continue

        match = FOOTNOTE_DEF_RE.match(lines[index])
        if match is None:
            index += 1
            continue
        label, first_line = match.groups()
        if label in definitions:
            raise ValueError(f"Duplicate footnote definition: {label}")
        body = [first_line]
        skipped_lines.add(index)
        next_index = index + 1
        while next_index < len(lines):
            continuation = lines[next_index]
            if continuation.startswith("\t"):
                body.append(continuation[1:])
                skipped_lines.add(next_index)
            elif continuation.startswith("    "):
                body.append(continuation[4:])
                skipped_lines.add(next_index)
            elif continuation.strip() == "" and next_index + 1 < len(lines) and (
                lines[next_index + 1].startswith("\t") or lines[next_index + 1].startswith("    ")
            ):
                body.append("")
                skipped_lines.add(next_index)
            else:
                break
            next_index += 1
        definitions[label] = "\n".join(body).rstrip()
        index = next_index

    referenced: list[str] = []
    active_fence = None
    for line_index, line in enumerate(lines):
        if line_index in skipped_lines:
            continue
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if active_fence is None:
                active_fence = marker
            elif marker[0] == active_fence[0] and len(marker) >= len(active_fence):
                active_fence = None
            continue
        if active_fence is None:
            referenced.extend(_footnote_labels_in_line(line))

    undefined = sorted(set(referenced) - set(definitions))
    if undefined:
        raise ValueError("Undefined footnote reference: " + ", ".join(undefined))

    ids: dict[str, int] = {}
    for label in referenced:
        if label not in ids:
            ids[label] = len(ids) + 1
    return definitions, skipped_lines, ids


def _add_footnote_reference(paragraph, label: str, context: ConversionContext) -> None:
    footnote_id = context.footnote_ids.get(label)
    if footnote_id is None:
        raise ValueError(f"Undefined footnote reference: {label}")
    run = paragraph.add_run()
    rpr = run._element.get_or_add_rPr()
    style = OxmlElement("w:rStyle")
    style.set(qn("w:val"), "FootnoteReference")
    rpr.append(style)
    reference = OxmlElement("w:footnoteReference")
    reference.set(qn("w:id"), str(footnote_id))
    run._element.append(reference)


def _render_inline(paragraph, text: str, context: ConversionContext) -> None:
    for token in _tokenize_inline(text):
        if token.kind == "text":
            _append_text(paragraph, token.text)
        elif token.kind == "bold":
            _append_text(paragraph, token.text, bold=True)
        elif token.kind == "code":
            _append_text(paragraph, token.text, code=True)
        elif token.kind == "link":
            _add_hyperlink(paragraph, token.target or token.text, token.text)
        elif token.kind == "footnote":
            _add_footnote_reference(paragraph, token.text, context)
        elif token.kind == "styled":
            _append_text(paragraph, token.text, bold=token.bold, color=token.color)


def _top_level_pipe_positions(text: str) -> list[int]:
    positions: list[int] = []
    index = 0
    active_ticks: str | None = None
    while index < len(text):
        if text[index] == "\\" and index + 1 < len(text):
            index += 2
            continue
        if text[index] == "`":
            count = 1
            while index + count < len(text) and text[index + count] == "`":
                count += 1
            marker = "`" * count
            if active_ticks is None:
                active_ticks = marker
            elif active_ticks == marker:
                active_ticks = None
            index += count
            continue
        if text[index] == "|" and active_ticks is None:
            positions.append(index)
        index += 1
    return positions


def _split_table_cells(line: str) -> list[str]:
    text = line.strip()
    positions = _top_level_pipe_positions(text)
    if not positions:
        return [text]
    cells: list[str] = []
    current: list[str] = []
    index = 0
    active_ticks: str | None = None
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            if text[index + 1] == "|":
                current.append("|")
            else:
                current.extend((char, text[index + 1]))
            index += 2
            continue
        if char == "`":
            count = 1
            while index + count < len(text) and text[index + count] == "`":
                count += 1
            marker = "`" * count
            if active_ticks is None:
                active_ticks = marker
            elif active_ticks == marker:
                active_ticks = None
            current.append(marker)
            index += count
            continue
        if char == "|" and active_ticks is None:
            cells.append("".join(current).strip())
            current.clear()
            index += 1
            continue
        current.append(char)
        index += 1
    cells.append("".join(current).strip())
    if positions[0] == 0:
        cells = cells[1:]
    if positions[-1] == len(text) - 1:
        cells = cells[:-1]
    return cells


def _is_table_separator(line: str) -> bool:
    cells = _split_table_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _is_table_row(line: str) -> bool:
    return bool(_top_level_pipe_positions(line.strip()))


def _style_table(table) -> None:
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row_index, row in enumerate(table.rows):
        for column_index, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if row_index == 0 else WD_ALIGN_PARAGRAPH.LEFT
                for run in paragraph.runs:
                    _set_run_font(run, size=9, bold=True if row_index == 0 else run.font.bold)
            if row_index == 0:
                cell_properties = cell._tc.get_or_add_tcPr()
                shading = OxmlElement("w:shd")
                shading.set(qn("w:val"), "clear")
                shading.set(qn("w:color"), "auto")
                shading.set(qn("w:fill"), "D9E2F3")
                cell_properties.append(shading)
            elif column_index == 0 and re.fullmatch(r"(?:\d+|[①②③④⑤⑥⑦⑧⑨⑩])", cell.text.strip()):
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _render_table(doc: Document, header: list[str], rows: list[list[str]], context: ConversionContext) -> None:
    width = max([len(header), *(len(row) for row in rows)] or [1])
    padded_header = header + [""] * (width - len(header))
    padded_rows = [row + [""] * (width - len(row)) for row in rows]
    table = doc.add_table(rows=1 + len(padded_rows), cols=width)
    for column_index, value in enumerate(padded_header):
        _render_inline(table.rows[0].cells[column_index].paragraphs[0], value, context)
    for row_index, row in enumerate(padded_rows, start=1):
        for column_index, value in enumerate(row):
            _render_inline(table.rows[row_index].cells[column_index].paragraphs[0], value, context)
    _style_table(table)


def _add_horizontal_rule(doc: Document) -> None:
    paragraph = doc.add_paragraph()
    properties = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "999999")
    borders.append(bottom)
    properties.append(borders)


def _is_horizontal_rule(text: str) -> bool:
    compact = text.replace(" ", "")
    return len(compact) >= 3 and len(set(compact)) == 1 and compact[0] in "-* _".replace(" ", "")


def _configure_document(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = CN_FONT
    normal.font.size = Pt(10.5)
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for field in ("w:eastAsia", "w:ascii", "w:hAnsi"):
        rfonts.set(qn(field), CN_FONT)
    for level, size in enumerate((18, 15, 13, 11.5, 10.5, 10), start=1):
        style = doc.styles[f"Heading {level}"]
        style.font.name = HEADING_FONT
        style.font.size = Pt(size)


def _render_fenced_code(doc: Document, code_lines: list[str]) -> None:
    paragraph = doc.add_paragraph(style="No Spacing")
    paragraph.paragraph_format.left_indent = Inches(0.2)
    for index, line in enumerate(code_lines):
        _append_text(paragraph, line, code=True)
        if index < len(code_lines) - 1:
            break_run = paragraph.add_run()
            _set_run_font(break_run, font_name=CODE_FONT, size=9.5)
            break_run.add_break()


def _footnote_run_xml(text: str, *, bold: bool = False, code: bool = False) -> str:
    rpr_parts = [
        "<w:rPr>",
        f'<w:rFonts w:eastAsia="{xml_escape(CODE_FONT if code else CN_FONT)}" '
        f'w:ascii="{xml_escape(CODE_FONT if code else CN_FONT)}" '
        f'w:hAnsi="{xml_escape(CODE_FONT if code else CN_FONT)}"/>',
        '<w:sz w:val="18"/>',
    ]
    if bold:
        rpr_parts.append("<w:b/>")
    if code:
        rpr_parts.append('<w:highlight w:val="lightGray"/>')
    rpr_parts.append("</w:rPr>")
    text_parts: list[str] = []
    parts = text.split("\n")
    for index, part in enumerate(parts):
        if part:
            text_parts.append(f'<w:t xml:space="preserve">{xml_escape(part)}</w:t>')
        if index < len(parts) - 1:
            text_parts.append("<w:br/>")
    if not text_parts:
        text_parts.append("<w:t/>")
    return "<w:r>" + "".join(rpr_parts + text_parts) + "</w:r>"


def _footnote_body_xml(text: str) -> str:
    runs: list[str] = []
    for token in _tokenize_inline(text, include_footnotes=False):
        if token.kind == "bold":
            runs.append(_footnote_run_xml(token.text, bold=True))
        elif token.kind == "code":
            runs.append(_footnote_run_xml(token.text, code=True))
        elif token.kind == "link":
            runs.append(_footnote_run_xml(f"{token.text} ({token.target})"))
        else:
            runs.append(_footnote_run_xml(token.text, bold=token.bold, code=False))
    return "".join(runs) or _footnote_run_xml("")


def _inject_footnotes(docx_path: Path, context: ConversionContext) -> int:
    """Add only referenced definitions to the OOXML package."""
    if not context.footnote_ids:
        return 0

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<w:footnotes xmlns:w="{FOOTNOTE_NS}">',
        '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>',
        '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>',
    ]
    for label, footnote_id in context.footnote_ids.items():
        body = _footnote_body_xml(context.footnote_definitions[label])
        parts.extend(
            (
                f'<w:footnote w:id="{footnote_id}">',
                '<w:p><w:pPr><w:pStyle w:val="FootnoteText"/></w:pPr>',
                '<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>',
                body,
                "</w:p></w:footnote>",
            )
        )
    parts.append("</w:footnotes>")

    with zipfile.ZipFile(docx_path, "r") as archive:
        content = {name: archive.read(name) for name in archive.namelist()}
    content["word/footnotes.xml"] = "".join(parts).encode("utf-8")

    content_types = etree.fromstring(content["[Content_Types].xml"])
    content_type_ns = content_types.nsmap.get(None)
    override_tag = f"{{{content_type_ns}}}Override"
    has_override = any(node.get("PartName") == "/word/footnotes.xml" for node in content_types)
    if not has_override:
        override = etree.Element(override_tag)
        override.set("PartName", "/word/footnotes.xml")
        override.set("ContentType", FOOTNOTE_CONTENT_TYPE)
        content_types.append(override)
    content["[Content_Types].xml"] = etree.tostring(content_types, xml_declaration=True, encoding="UTF-8", standalone=True)

    rels_name = "word/_rels/document.xml.rels"
    relationships = etree.fromstring(content[rels_name])
    relationship_ns = relationships.nsmap.get(None)
    has_relationship = any(node.get("Type") == FOOTNOTE_REL for node in relationships)
    if not has_relationship:
        existing_ids = []
        for node in relationships:
            match = re.fullmatch(r"rId(\d+)", node.get("Id", ""))
            if match:
                existing_ids.append(int(match.group(1)))
        relationship = etree.Element(f"{{{relationship_ns}}}Relationship")
        relationship.set("Id", f"rId{max(existing_ids, default=0) + 1}")
        relationship.set("Type", FOOTNOTE_REL)
        relationship.set("Target", "footnotes.xml")
        relationships.append(relationship)
    content[rels_name] = etree.tostring(relationships, xml_declaration=True, encoding="UTF-8", standalone=True)

    temporary = docx_path.with_suffix(docx_path.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in content.items():
            archive.writestr(name, data)
    shutil.move(temporary, docx_path)
    return len(context.footnote_ids)


def _post_annotate(docx_path: Path) -> int:
    """Run the sibling comment converter from the actual script directory."""
    converter_path = Path(__file__).resolve().with_name("annotations_to_docx_comments.py")
    if not converter_path.is_file():
        raise RuntimeError(f"Annotation converter is missing: {converter_path}")
    spec = importlib.util.spec_from_file_location("annotations_to_docx_comments", converter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the annotation converter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.convert_docx_annotations(str(docx_path)))


def convert(markdown_path: str | Path, docx_path: str | Path, *, convert_annotations: bool = True) -> Path:
    """Convert one Markdown file and return the resulting DOCX path."""
    markdown_path = Path(markdown_path)
    docx_path = Path(docx_path)
    text = markdown_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    definitions, skipped_lines, footnote_ids = _collect_footnotes(lines)
    context = ConversionContext(definitions, footnote_ids)

    document = Document()
    _configure_document(document)
    index = 0
    while index < len(lines):
        if index in skipped_lines:
            index += 1
            continue
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            code_lines: list[str] = []
            cursor = index + 1
            while cursor < len(lines):
                closing = FENCE_RE.match(lines[cursor])
                if closing and closing.group(1)[0] == marker[0] and len(closing.group(1)) >= len(marker):
                    break
                code_lines.append(lines[cursor])
                cursor += 1
            _render_fenced_code(document, code_lines)
            index = cursor + 1 if cursor < len(lines) else cursor
            continue

        heading = HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            paragraph = document.add_heading(level=level)
            _render_inline(paragraph, heading.group(2).strip(), context)
            index += 1
            continue

        if _is_horizontal_rule(stripped):
            _add_horizontal_rule(document)
            index += 1
            continue

        if index + 1 < len(lines) and _is_table_row(line) and _is_table_separator(lines[index + 1]):
            header = _split_table_cells(line)
            rows: list[list[str]] = []
            cursor = index + 2
            while cursor < len(lines) and _is_table_row(lines[cursor]):
                rows.append(_split_table_cells(lines[cursor]))
                cursor += 1
            _render_table(document, header, rows, context)
            index = cursor
            continue

        if stripped.startswith(">"):
            quote_lines: list[str] = []
            cursor = index
            while cursor < len(lines) and lines[cursor].lstrip().startswith(">"):
                quote_lines.append(lines[cursor].lstrip()[1:].lstrip())
                cursor += 1
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.3)
            paragraph.paragraph_format.right_indent = Inches(0.3)
            properties = paragraph._p.get_or_add_pPr()
            borders = OxmlElement("w:pBdr")
            left = OxmlElement("w:left")
            left.set(qn("w:val"), "single")
            left.set(qn("w:sz"), "12")
            left.set(qn("w:space"), "8")
            left.set(qn("w:color"), "4472C4")
            borders.append(left)
            properties.append(borders)
            _render_inline(paragraph, "\n".join(quote_lines), context)
            index = cursor
            continue

        unordered = UNORDERED_LIST_RE.match(stripped)
        if unordered:
            paragraph = document.add_paragraph(style="List Bullet")
            _render_inline(paragraph, unordered.group(1), context)
            index += 1
            continue

        ordered = ORDERED_LIST_RE.match(stripped)
        if ordered:
            paragraph = document.add_paragraph(style="List Number")
            _render_inline(paragraph, ordered.group(1), context)
            index += 1
            continue

        paragraph = document.add_paragraph()
        _render_inline(paragraph, stripped, context)
        index += 1

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(docx_path)
    _inject_footnotes(docx_path, context)
    if convert_annotations:
        _post_annotate(docx_path)
    return docx_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="将 Markdown 报告转换为 DOCX")
    parser.add_argument("markdown", help="输入 Markdown 文件")
    parser.add_argument("docx", help="输出 DOCX 文件")
    parser.add_argument(
        "--no-annotations",
        action="store_true",
        help="保留末尾批注章节，不转换为 Word 批注",
    )
    args = parser.parse_args(argv)
    try:
        output = convert(args.markdown, args.docx, convert_annotations=not args.no_annotations)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"md_to_docx: {error}", file=sys.stderr)
        return 1
    print(f"saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

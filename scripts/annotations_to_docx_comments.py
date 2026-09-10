#!/usr/bin/env python3
"""Move the final internal annotation chapter of a DOCX into real Word comments."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsmap, qn
from docx.opc.packuri import PackURI
from docx.opc.part import XmlPart
from docx.text.paragraph import Paragraph


W = nsmap["w"]
COMMENTS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
COMMENTS_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
ANNOTATION_TITLES = {"批注", "批注（判断过程、思路与假设）"}
MARKDOWN_SUBSECTION_RE = re.compile(r"^###\s+\d+[.、][ \t]*(.+?)[ \t]*$", re.MULTILINE)


def _paragraph_text(element) -> str:
    return "".join(node.text or "" for node in element.iter(qn("w:t")))


def _heading_level(element) -> int | None:
    if element.tag != qn("w:p"):
        return None
    properties = element.find(qn("w:pPr"))
    if properties is None:
        return None
    style = properties.find(qn("w:pStyle"))
    if style is None:
        return None
    value = style.get(qn("w:val"), "")
    match = re.fullmatch(r"Heading ?([1-9])", value, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _annotation_start(children) -> tuple[int, int] | None:
    """Find only a heading whose text is the annotation chapter title."""
    for index, element in enumerate(children):
        level = _heading_level(element)
        if level is None:
            continue
        text = _paragraph_text(element).strip()
        if text in ANNOTATION_TITLES:
            return index, level
    return None


def _element_text(element) -> str:
    if element.tag == qn("w:tbl"):
        row_texts: list[str] = []
        for row in element.findall(qn("w:tr")):
            cells = []
            for cell in row.findall(qn("w:tc")):
                cell_text = "\n".join(
                    _paragraph_text(paragraph).strip()
                    for paragraph in cell.findall(qn("w:p"))
                    if _paragraph_text(paragraph).strip()
                )
                cells.append(cell_text)
            if any(cells):
                row_texts.append(" | ".join(cells))
        return "\n".join(row_texts)
    return _paragraph_text(element)


def _join_elements(elements) -> str:
    parts = [_element_text(element).strip() for element in elements]
    return "\n".join(part for part in parts if part)


def parse_annotations(markdown_text: str) -> list[tuple[str, str]]:
    """Parse the Markdown representation of an annotation chapter for callers that need it."""
    matches = list(MARKDOWN_SUBSECTION_RE.finditer(markdown_text))
    if not matches:
        body = markdown_text.strip()
        return [("批注", body)] if body else []
    entries: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        body = markdown_text[match.end() : end].strip()
        if body:
            entries.append((match.group(1).strip(), body))
    return entries


def extract_and_strip_annotations(doc: Document) -> list[tuple[str, str]]:
    """Extract a structured final annotation chapter and leave section properties intact."""
    body = doc.element.body
    children = list(body)
    found = _annotation_start(children)
    if found is None:
        return []
    start, container_level = found
    end = len(children)
    for index in range(start, len(children)):
        if children[index].tag == qn("w:sectPr"):
            end = index
            break

    removed = children[start:end]
    entries: list[tuple[str, str]] = []
    current_title: str | None = None
    current_body: list = []
    container_body: list = []

    for element in removed[1:]:
        level = _heading_level(element)
        if level is not None and level > container_level:
            if current_title is not None:
                body_text = _join_elements(current_body)
                if body_text:
                    entries.append((current_title, body_text))
            current_title = _paragraph_text(element).strip()
            current_body = []
        elif current_title is None:
            container_body.append(element)
        else:
            current_body.append(element)

    if current_title is not None:
        body_text = _join_elements(current_body)
        if body_text:
            entries.append((current_title, body_text))
    elif container_body:
        body_text = _join_elements(container_body)
        if body_text:
            entries.append(("批注", body_text))

    for element in removed:
        body.remove(element)
    return entries


def _get_or_create_comments_part(doc: Document):
    for relationship in doc.part.rels.values():
        if relationship.reltype == COMMENTS_REL:
            return relationship.target_part
    comments_element = parse_xml(f'<w:comments xmlns:w="{W}"/>')
    comments_part = XmlPart(
        PackURI("/word/comments.xml"),
        COMMENTS_CONTENT_TYPE,
        comments_element,
        doc.part.package,
    )
    doc.part.relate_to(comments_part, COMMENTS_REL)
    return comments_part


def _ensure_comment_styles(doc: Document) -> None:
    styles = doc.styles.element
    present = {style.get(qn("w:styleId")) for style in styles.findall(qn("w:style"))}
    for style_id, style_type, display_name in (
        ("CommentReference", "character", "Comment Reference"),
        ("CommentText", "paragraph", "Comment Text"),
    ):
        if style_id in present:
            continue
        style = OxmlElement("w:style")
        style.set(qn("w:type"), style_type)
        style.set(qn("w:styleId"), style_id)
        name = OxmlElement("w:name")
        name.set(qn("w:val"), display_name)
        style.append(name)
        styles.append(style)


def _next_comment_id(comments_part) -> int:
    ids = []
    for comment in comments_part.element.iter(qn("w:comment")):
        raw_id = comment.get(qn("w:id"))
        if raw_id is not None and raw_id.lstrip("-").isdigit():
            ids.append(int(raw_id))
    return max(ids, default=-1) + 1


def _paragraphs(doc: Document) -> list[Paragraph]:
    return [Paragraph(element, doc) for element in doc.element.body.findall(qn("w:p"))]


def _find_anchor(doc: Document, title: str) -> Paragraph:
    title_rules = (
        (("事实", "画像", "更正"), ("已知与待核事实", "事实")),
        (("来源", "版本", "核验"), ("来源与效力核验", "适用性结果")),
        (("假设", "适用", "角色"), ("适用性结果", "产品落地清单")),
    )
    paragraphs = _paragraphs(doc)
    for title_words, anchor_words in title_rules:
        if any(word in title for word in title_words):
            for paragraph in paragraphs:
                if any(word in paragraph.text for word in anchor_words):
                    return paragraph
    if paragraphs:
        return paragraphs[-1]
    return doc.add_paragraph()


def _append_comment_text(comment, text: str) -> None:
    paragraph = OxmlElement("w:p")
    properties = OxmlElement("w:pPr")
    style = OxmlElement("w:pStyle")
    style.set(qn("w:val"), "CommentText")
    properties.append(style)
    paragraph.append(properties)
    run = OxmlElement("w:r")
    for index, line in enumerate(text.split("\n")):
        if line:
            node = OxmlElement("w:t")
            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            node.text = line
            run.append(node)
        if index < len(text.split("\n")) - 1:
            run.append(OxmlElement("w:br"))
    if len(run) == 0:
        run.append(OxmlElement("w:t"))
    paragraph.append(run)
    comment.append(paragraph)


def _add_comment(comments_part, anchor: Paragraph, comment_id: int, title: str, body: str, author: str) -> None:
    if not anchor._p.findall(qn("w:r")):
        anchor.add_run(" ")
    start = OxmlElement("w:commentRangeStart")
    start.set(qn("w:id"), str(comment_id))
    anchor._p.insert(0, start)
    end = OxmlElement("w:commentRangeEnd")
    end.set(qn("w:id"), str(comment_id))
    reference_run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    style = OxmlElement("w:rStyle")
    style.set(qn("w:val"), "CommentReference")
    properties.append(style)
    reference_run.append(properties)
    reference = OxmlElement("w:commentReference")
    reference.set(qn("w:id"), str(comment_id))
    reference_run.append(reference)
    anchor._p.append(end)
    anchor._p.append(reference_run)

    comment = OxmlElement("w:comment")
    comment.set(qn("w:id"), str(comment_id))
    comment.set(qn("w:author"), author)
    comment.set(qn("w:initials"), author[:4] or "AI")
    comment.set(qn("w:date"), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    _append_comment_text(comment, f"{title}\n\n{body}")
    comments_part.element.append(comment)


def convert_docx_annotations(docx_path: str | Path, author: str = "合规分析") -> int:
    """Move one final annotation chapter into comments and return the new count."""
    path = Path(docx_path)
    doc = Document(path)
    had_annotation_chapter = _annotation_start(list(doc.element.body)) is not None
    entries = extract_and_strip_annotations(doc)
    if not had_annotation_chapter:
        return 0
    if not entries:
        doc.save(path)
        return 0
    _ensure_comment_styles(doc)
    comments_part = _get_or_create_comments_part(doc)
    comment_id = _next_comment_id(comments_part)
    added = 0
    for title, body in entries:
        if not body.strip():
            continue
        _add_comment(comments_part, _find_anchor(doc, title), comment_id, title, body, author)
        comment_id += 1
        added += 1
    doc.save(path)
    return added


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="将末尾批注章节转换为 Word 批注")
    parser.add_argument("docx", help="待处理的 DOCX 文件")
    parser.add_argument("--author", default="合规分析", help="批注作者")
    args = parser.parse_args(argv)
    count = convert_docx_annotations(args.docx, author=args.author)
    print(f"converted {count} annotation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

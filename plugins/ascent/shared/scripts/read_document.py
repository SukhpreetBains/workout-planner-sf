#!/usr/bin/env python3
"""Convert a document to plain Markdown so the agent can read it.

Usage:
    py read_document.py "workspace/inbox/Kickoff Notes.docx" [--out PATH]

Supports .docx, .pdf, .pptx, .xlsx. Prints Markdown to stdout, or writes it
to --out. Text files (.md, .txt, .csv, ...) need no conversion — read those
directly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import REPO_ROOT

MAX_CHARS = 400_000  # guardrail against runaway conversions


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# Deleted and moved-away text is not part of the current wording, and
# markup-compatibility fallbacks repeat content already in their Choice.
DOCX_SKIPPED = {W + "del", W + "moveFrom",
                "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"}


def markdown_table(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * len(rows[0])]
    return lines + ["| " + " | ".join(row) + " |" for row in rows[1:]]


def docx_visible_text(element) -> str:
    """Current wording of a paragraph, with tracked insertions included."""
    parts: list[str] = []

    def walk(node) -> None:
        for child in node:
            if child.tag in DOCX_SKIPPED:
                continue
            if child.tag == W + "t":
                parts.append(child.text or "")
            elif child.tag in (W + "tab", W + "br", W + "cr"):
                parts.append(" ")
            else:
                walk(child)

    walk(element)
    return "".join(parts)


def docx_paragraphs(container):
    for child in container:
        if child.tag in DOCX_SKIPPED:
            continue
        if child.tag == W + "p":
            yield child
        else:
            yield from docx_paragraphs(child)


def docx_table_rows(tbl) -> list[list[str]]:
    rows = []
    for tr in tbl.iterchildren(W + "tr"):
        cells = []
        for tc in tr.iterchildren(W + "tc"):
            texts = (docx_visible_text(p).strip() for p in docx_paragraphs(tc))
            cells.append(" ".join(t for t in texts if t))
        if cells:
            rows.append(cells)
    return rows


def docx_tracked_changes(root) -> list[str]:
    changes: list[list] = []
    for element in root.iter(W + "ins", W + "del"):
        inserted = element.tag == W + "ins"
        text = "".join(t.text or "" for t in element.iter(W + "t" if inserted else W + "delText"))
        if not text.strip():
            continue
        kind = "Inserted" if inserted else "Deleted"
        author = element.get(W + "author") or "unknown author"
        paragraph = next(element.iterancestors(W + "p"), None)
        if changes and changes[-1][0] is paragraph and changes[-1][1:3] == [kind, author]:
            changes[-1][3] += text
        else:
            changes.append([paragraph, kind, author, text])
    return [f'- {kind} by {author}: "{" ".join(text.split())}"'
            for _, kind, author, text in changes]


def read_docx(path: Path) -> str:
    import docx
    from docx.text.paragraph import Paragraph

    doc = docx.Document(path)
    parts: list[str] = []

    def walk_blocks(container) -> None:
        for child in container:
            if child.tag == W + "p":
                text = docx_visible_text(child).strip()
                if not text:
                    continue
                style = (Paragraph(child, doc).style.name or "").lower()
                if style.startswith("heading"):
                    level = "".join(ch for ch in style if ch.isdigit()) or "2"
                    parts.append("#" * min(int(level), 6) + " " + text)
                else:
                    parts.append(text)
            elif child.tag == W + "tbl":
                table = markdown_table(docx_table_rows(child))
                if table:
                    parts.append("\n".join(table))
            elif child.tag == W + "sdt":
                for content in child.iterchildren(W + "sdtContent"):
                    walk_blocks(content)

    walk_blocks(doc.element.body)
    changes = docx_tracked_changes(doc.element.body)
    if changes:
        parts.append("## Tracked changes\n\nThe text above shows the document with "
                     "these changes applied.\n\n" + "\n".join(changes))
    return "\n\n".join(parts)


def read_pdf(path: Path) -> str:
    import fitz  # pymupdf

    parts = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, 1):
            text = page.get_text().strip()
            if text:
                parts.append(f"## Page {i}\n\n{text}")
    return "\n\n".join(parts)


def pptx_shape_lines(shapes) -> list[str]:
    from pptx.shapes.group import GroupShape

    lines: list[str] = []
    for shape in shapes:
        if isinstance(shape, GroupShape):
            lines += pptx_shape_lines(shape.shapes)
        elif shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                text = "".join(run.text for run in para.runs).strip()
                if text:
                    lines.append(f"- {text}")
        elif getattr(shape, "has_table", False):
            rows = [[cell.text.strip().replace("\n", " ") for cell in row.cells]
                    for row in shape.table.rows]
            table = markdown_table(rows)
            if table:
                lines += ["", *table, ""]
    return lines


def read_pptx(path: Path) -> str:
    from pptx import Presentation

    parts = []
    for i, slide in enumerate(Presentation(path).slides, 1):
        lines = [f"## Slide {i}", *pptx_shape_lines(slide.shapes)]
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                lines.append(f"- Speaker notes: {notes}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def read_xlsx(path: Path) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        rows = [["" if v is None else str(v) for v in row]
                for row in ws.iter_rows(values_only=True)]
        rows = [r for r in rows if any(v.strip() for v in r)]
        if not rows:
            continue
        lines = [f"## Sheet: {ws.title}",
                 "| " + " | ".join(rows[0]) + " |",
                 "|" + " --- |" * len(rows[0])]
        lines += ["| " + " | ".join(r) + " |" for r in rows[1:500]]
        if len(rows) > 500:
            lines.append(f"... {len(rows) - 500} more rows truncated")
        parts.append("\n".join(lines))
    wb.close()
    return "\n\n".join(parts)


READERS = {".docx": read_docx, ".pdf": read_pdf, ".pptx": read_pptx, ".xlsx": read_xlsx}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--out")
    args = parser.parse_args()
    path = Path(args.path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        print(f"not found: {args.path}")
        return 1
    reader = READERS.get(path.suffix.lower())
    if reader is None:
        print(f"unsupported type '{path.suffix}' — supported: {', '.join(READERS)}. "
              "Plain-text files can be read directly.")
        return 1
    text = reader(path)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + f"\n\n[truncated at {MAX_CHARS} characters]"
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = REPO_ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

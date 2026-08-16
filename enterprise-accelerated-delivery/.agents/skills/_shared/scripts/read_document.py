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


def read_docx(path: Path) -> str:
    import docx

    doc = docx.Document(path)
    parts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name or "").lower()
        if style.startswith("heading"):
            level = "".join(ch for ch in style if ch.isdigit()) or "2"
            parts.append("#" * min(int(level), 6) + " " + text)
        else:
            parts.append(text)
    for table in doc.tables:
        rows = [[cell.text.strip().replace("\n", " ") for cell in row.cells]
                for row in table.rows]
        if rows:
            parts.append("| " + " | ".join(rows[0]) + " |")
            parts.append("|" + " --- |" * len(rows[0]))
            parts += ["| " + " | ".join(r) + " |" for r in rows[1:]]
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


def read_pptx(path: Path) -> str:
    from pptx import Presentation

    parts = []
    for i, slide in enumerate(Presentation(path).slides, 1):
        lines = [f"## Slide {i}"]
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = "".join(run.text for run in para.runs).strip()
                    if text:
                        lines.append(f"- {text}")
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

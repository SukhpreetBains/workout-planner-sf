#!/usr/bin/env python3
"""Select the next batch of inbox source documents for workspace-add.

Prints JSON: up to three original sources, oldest modification time first
with filename as the tie breaker. A Markdown file whose stem matches a
convertible original (for example `Report.md` beside `Report.pdf`) is that
original's converted copy: it is attached to the original and never counted
as a separate source. Hidden files are ignored. Read-only.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import INBOX, rel  # noqa: E402
from read_document import READERS  # noqa: E402

BATCH_SIZE = 3


def inbox_sources(inbox: Path) -> list[dict]:
    if not inbox.is_dir():
        return []
    files = [p for p in inbox.iterdir() if p.is_file() and not p.name.startswith(".")]
    convertible_stems = {p.stem for p in files if p.suffix.lower() in READERS}
    copies = {p.stem: p for p in files if p.suffix.lower() == ".md" and p.stem in convertible_stems}
    originals = [p for p in files if p not in copies.values()]
    originals.sort(key=lambda p: (p.stat().st_mtime, p.name))
    return [
        {
            "path": rel(p),
            "converted_copy": rel(copies[p.stem]) if p.suffix.lower() in READERS and p.stem in copies else None,
            "modified": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
        }
        for p in originals
    ]


def main() -> int:
    sources = inbox_sources(INBOX)
    selected = sources[:BATCH_SIZE]
    print(json.dumps({
        "batch_size": BATCH_SIZE,
        "selected": selected,
        "remaining": len(sources) - len(selected),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

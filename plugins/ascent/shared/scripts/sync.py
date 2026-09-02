#!/usr/bin/env python3
"""Keep the derived state in sync with the workspace.

Usage:
    py sync.py            # rebuild tracker copies + search index, save state
    py sync.py --status   # report what is new/changed since the last sync
                          # and which documents have not been extracted yet

Sync maintains three things under workspace/.system/:
  tracker-copies/<category>.yaml   plain-text copies of every tracker tab,
                                   so agents can read/grep rows without Excel
  search/index.sqlite              full-text index (SQLite FTS5) over
                                   workspace documents and tracker rows
  sync-state.json                  file hashes from the last sync, used by
                                   --status to spot new or changed files
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import (
    INBOX,
    INDEXED_FOLDERS,
    INDEXED_SUFFIXES,
    REPO_ROOT,
    SEARCH_DB,
    SOURCES_FILE,
    SYNC_STATE,
    TRACKER_COPIES_DIR,
    WORKSPACE,
    load_schema,
    rel,
)
from trackers import id_column, read_rows


def workspace_files() -> list[Path]:
    files = []
    for folder in INDEXED_FOLDERS:
        base = WORKSPACE / folder
        if base.is_dir():
            files += [p for p in sorted(base.rglob("*"))
                      if p.is_file() and p.suffix.lower() in INDEXED_SUFFIXES]
    return files


def file_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def export_tracker_copies(schema: dict) -> int:
    TRACKER_COPIES_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for cat in schema["categories"]:
        rows = read_rows(cat, schema)
        out = TRACKER_COPIES_DIR / f"{cat}.yaml"
        out.write_text(
            yaml.safe_dump({"category": cat, "count": len(rows), "rows": rows},
                           sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )
        total += len(rows)
    return total


def build_search_index(schema: dict, files: list[Path]) -> int:
    SEARCH_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(SEARCH_DB)
    con.execute("DROP TABLE IF EXISTS docs")
    con.execute(
        "CREATE VIRTUAL TABLE docs USING fts5(kind, ref, title, content, "
        "tokenize='porter unicode61')"
    )
    count = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        con.execute("INSERT INTO docs VALUES ('document', ?, ?, ?)",
                    (rel(path), path.stem, text))
        count += 1
    for cat in schema["categories"]:
        idcol = id_column(cat, schema)
        for row in read_rows(cat, schema):
            content = "\n".join(f"{k}: {v}" for k, v in row.items() if v)
            con.execute("INSERT INTO docs VALUES (?, ?, ?, ?)",
                        (cat, row.get(idcol, ""), row.get(idcol, ""), content))
            count += 1
    con.commit()
    con.close()
    return count


def extracted_sources() -> set[str]:
    if not SOURCES_FILE.exists():
        return set()
    doc = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8")) or {}
    return {s["path"] for s in doc.get("sources", [])
            if isinstance(s, dict) and s.get("status") == "extracted"}


def status() -> int:
    state = {}
    if SYNC_STATE.exists():
        state = json.loads(SYNC_STATE.read_text(encoding="utf-8"))
    known = state.get("files", {})
    current = {rel(p): file_hash(p) for p in workspace_files()}

    new = sorted(set(current) - set(known))
    changed = sorted(p for p in current if p in known and known[p] != current[p])
    removed = sorted(set(known) - set(current))
    inbox = sorted(rel(p) for p in INBOX.rglob("*")
                   if p.is_file() and p.name != ".gitkeep") if INBOX.is_dir() else []
    unextracted = sorted(set(current) - extracted_sources()
                         - {p for p in current if p.startswith("workspace/project/")})

    print(f"last sync: {state.get('last_sync', 'never')}")
    for label, items in [("inbox files waiting", inbox),
                         ("new since last sync", new),
                         ("changed since last sync", changed),
                         ("removed since last sync", removed),
                         ("not yet extracted into trackers", unextracted)]:
        print(f"{label}: {len(items)}")
        for item in items[:20]:
            print(f"  - {item}")
        if len(items) > 20:
            print(f"  ... and {len(items) - 20} more")
    if inbox or new or changed or removed:
        print("run 'py sync.py' after processing to bring derived state up to date")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        return status()

    schema = load_schema()
    files = workspace_files()
    rows = export_tracker_copies(schema)
    indexed = build_search_index(schema, files)

    SYNC_STATE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE.write_text(json.dumps({
        "last_sync": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "files": {rel(p): file_hash(p) for p in files},
    }, indent=2), encoding="utf-8")

    print(f"synced: {rows} tracker rows copied, {indexed} items indexed "
          f"from {len(files)} documents + trackers")
    return 0


if __name__ == "__main__":
    sys.exit(main())

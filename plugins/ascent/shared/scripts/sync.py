#!/usr/bin/env python3
"""Keep the derived state in sync with the workspace.

Usage:
    py sync.py            # rebuild tracker copies + search index, save state
    py sync.py --trackers-only  # refresh current rows without scanning documents
    py sync.py --status   # report what is new/changed since the last sync
                          # and which documents have not been extracted yet
    py sync.py --check-setup  # cheap, read-only: does this look like an
                          # initialized Opportunity workspace at all? For any
                          # workspace-dependent skill to call before assuming
                          # one exists — does not require Python deps beyond
                          # this script's own (yaml), does no scanning or
                          # parsing of tracker/document content.

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
    PROJECT_FILE,
    REPO_ROOT,
    SEARCH_DB,
    SOURCES_FILE,
    SYNC_STATE,
    SYSTEM_DIR,
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


def check_setup() -> int:
    """Cheap, read-only precondition check: does this look like an
    initialized Opportunity workspace? Filesystem existence only — no
    workbook parsing, no document scanning, safe to call before every
    workspace-dependent skill's real work starts."""
    schema = load_schema()
    tracker_files = sorted({t["file"] for t in schema["trackers"].values()})
    missing_trackers = [f for f in tracker_files if not (REPO_ROOT / f).exists()]

    workspace_ready = WORKSPACE.is_dir()
    system_ready = SYSTEM_DIR.is_dir()
    trackers_ready = workspace_ready and not missing_trackers
    identity_ready = PROJECT_FILE.exists()

    print(f"workspace/: {'found' if workspace_ready else 'MISSING'}")
    print(f"workspace/.system/: {'found' if system_ready else 'MISSING'}")
    print(f"trackers: {len(tracker_files) - len(missing_trackers)}/{len(tracker_files)} initialized"
          + (f" (missing: {', '.join(missing_trackers)})" if missing_trackers else ""))
    print(f"identity (workspace/.system/project.yaml): {'found' if identity_ready else 'MISSING'}")

    if workspace_ready and system_ready and trackers_ready:
        print("ready: this looks like an initialized Opportunity workspace")
    else:
        print("not ready: this does not look like an initialized Opportunity workspace — run initial-setup first")
    return 0


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--trackers-only", action="store_true")
    mode.add_argument("--check-setup", action="store_true")
    args = parser.parse_args()
    if args.check_setup:
        return check_setup()
    if args.status:
        return status()

    schema = load_schema()
    if args.trackers_only:
        rows = export_tracker_copies(schema)
        print(f"synced: {rows} tracker rows copied; document index and sync state unchanged")
        return 0

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

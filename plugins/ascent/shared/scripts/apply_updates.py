#!/usr/bin/env python3
"""Apply an approved proposed-updates file to the tracker workbooks.

Usage:
    py apply_updates.py workspace/.system/proposed-updates/<file>.yaml [--keep]

Validates first (same checks as validate_updates.py), then writes every
update, prints the assigned IDs, moves the file to
workspace/.system/applied-updates/, and runs sync.py. --keep leaves the
file in proposed-updates (useful when applying a subset was rejected and
the file was edited).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import APPLIED_UPDATES_DIR, REPO_ROOT, load_schema
from trackers import id_column, upsert_row
from validate_updates import load_updates, validate


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--keep"]
    keep = "--keep" in sys.argv
    if len(args) != 1:
        print(__doc__)
        return 1
    path = Path(args[0])
    if not path.is_absolute():
        path = REPO_ROOT / path

    doc = load_updates(path)
    schema = load_schema()
    problems = validate(doc, schema)
    if problems:
        print(f"NOT APPLIED: {len(problems)} validation problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1

    default_refs = doc.get("source_refs") or []
    applied = []
    for upd in doc["updates"]:
        cat = upd["category"]
        fields = dict(upd.get("fields") or {})
        if upd.get("action", "add") == "update":
            fields[id_column(cat, schema)] = upd["id"]
        else:
            for col in schema["categories"][cat]["columns"]:
                if col.get("required") and not str(fields.get(col["name"], "")).strip():
                    fields[col["name"]] = col.get("default", "")
        refs = upd.get("source_refs") or default_refs
        fields["Source Refs"] = schema["list_delimiter"].join(refs)
        row_id = upsert_row(cat, fields, schema)
        applied.append((upd.get("action", "add"), cat, row_id))

    for action, cat, row_id in applied:
        print(f"{action}: {cat} {row_id}")

    if not keep:
        APPLIED_UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        path.rename(APPLIED_UPDATES_DIR / path.name)

    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("sync.py"))],
        capture_output=True, text=True,
    )
    print(result.stdout.strip() or result.stderr.strip())
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

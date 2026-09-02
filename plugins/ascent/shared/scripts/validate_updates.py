#!/usr/bin/env python3
"""Validate a proposed-updates YAML file against the tracker schema.

Usage:
    py validate_updates.py workspace/.system/proposed-updates/<file>.yaml

Exit 0 with "OK: N updates valid" or exit 1 listing every problem found.

Update file format:
    source_refs: [workspace/meetings/2026-08-14 - Kickoff.md]   # default refs
    updates:
      - category: pain_point
        action: add                # add | update
        # id: PAIN-003             # required when action is update
        fields:
          Statement: "..."
          Severity: high
        # source_refs: [...]       # optional per-update override
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import REPO_ROOT, load_schema
from trackers import id_column, normalize_enum, read_rows


def contained_source(ref: str) -> Path | None:
    try:
        path = (REPO_ROOT / ref).resolve()
        path.relative_to(REPO_ROOT)
        return path
    except (OSError, ValueError):
        return None


def load_updates(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict) or not isinstance(doc.get("updates"), list):
        raise ValueError("file must be a mapping with an 'updates' list")
    return doc


def validate(doc: dict, schema: dict) -> list[str]:
    problems: list[str] = []
    default_refs = doc.get("source_refs") or []
    existing_ids: dict[str, set[str]] = {}

    def ids_for(category: str) -> set[str]:
        if category not in existing_ids:
            col = id_column(category, schema)
            existing_ids[category] = {r.get(col, "") for r in read_rows(category, schema)}
        return existing_ids[category]

    for i, upd in enumerate(doc["updates"], 1):
        where = f"update {i}"
        cat_name = upd.get("category", "")
        cat = schema["categories"].get(cat_name)
        if cat is None:
            problems.append(f"{where}: unknown category '{cat_name}' "
                            f"(valid: {', '.join(schema['categories'])})")
            continue
        where = f"update {i} ({cat_name})"

        action = upd.get("action", "add")
        if action not in ("add", "update"):
            problems.append(f"{where}: action must be 'add' or 'update', got '{action}'")
        if action == "update":
            rid = upd.get("id", "")
            if not rid:
                problems.append(f"{where}: action 'update' needs an 'id'")
            elif rid not in ids_for(cat_name):
                problems.append(f"{where}: id '{rid}' does not exist in the tracker")

        fields = upd.get("fields") or {}
        if not isinstance(fields, dict):
            problems.append(f"{where}: fields must be a mapping")
            continue
        cols = {c["name"]: c for c in cat["columns"]}
        for name in fields:
            if name not in cols:
                problems.append(f"{where}: unknown column '{name}' "
                                f"(valid: {', '.join(cols)})")
        if action == "add":
            for name, col in cols.items():
                if col.get("required") and not str(fields.get(name, "")).strip():
                    if "default" in col:
                        fields[name] = col["default"]
                    else:
                        problems.append(f"{where}: required column '{name}' is missing")
        for name, col in cols.items():
            raw_value = fields.get(name, "")
            value = str(raw_value).strip()
            if not value:
                continue
            if "enum" in col:
                normalized = normalize_enum(value)
                fields[name] = normalized
                value = normalized
            if "enum" in col and value not in col["enum"]:
                problems.append(f"{where}: '{name}' must be one of "
                                f"{col['enum']}, got '{value}'")
            if col.get("type") == "number":
                try:
                    number = float(raw_value)
                    if "minimum" in col and number < col["minimum"]:
                        problems.append(f"{where}: '{name}' must be at least {col['minimum']}")
                    if "maximum" in col and number > col["maximum"]:
                        problems.append(f"{where}: '{name}' must be at most {col['maximum']}")
                    fields[name] = number
                except (TypeError, ValueError):
                    problems.append(f"{where}: '{name}' must be a number")
            if col.get("type") == "date":
                try:
                    if not isinstance(raw_value, (date, datetime)):
                        datetime.fromisoformat(value)
                except ValueError:
                    problems.append(f"{where}: '{name}' must be an ISO date")
            if "links_to" in col:
                for linked in [v.strip() for v in value.split(";") if v.strip()]:
                    if linked not in ids_for(col["links_to"]):
                        problems.append(f"{where}: '{name}' points at '{linked}' "
                                        f"which is not an existing {col['links_to']} ID")
            if "links_to_any" in col:
                valid_ids = set()
                for linked_category in col["links_to_any"]:
                    valid_ids.update(ids_for(linked_category))
                for linked in [v.strip() for v in value.split(";") if v.strip()]:
                    if linked not in valid_ids:
                        problems.append(f"{where}: '{name}' points at '{linked}' which is not "
                                        "an existing RAIDD ID")

        refs = upd.get("source_refs") or default_refs
        if not refs:
            problems.append(f"{where}: no source_refs (each update must cite "
                            "the document it came from)")
        for ref in refs:
            source_path = contained_source(str(ref))
            if source_path is None:
                problems.append(f"{where}: source ref '{ref}' escapes the workspace root")
            elif not source_path.exists():
                problems.append(f"{where}: source ref '{ref}' does not exist")
        evidence = upd.get("evidence") or []
        if not isinstance(evidence, list):
            problems.append(f"{where}: evidence must be a list")
        for entry in evidence if isinstance(evidence, list) else []:
            if not isinstance(entry, dict) or not entry.get("source_ref"):
                problems.append(f"{where}: each evidence entry needs source_ref")
    return problems


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    path = Path(sys.argv[1])
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        doc = load_updates(path)
    except Exception as exc:  # surface YAML/shape errors plainly
        print(f"INVALID: {exc}")
        return 1
    problems = validate(doc, load_schema())
    if problems:
        print(f"INVALID: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: {len(doc['updates'])} update(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())

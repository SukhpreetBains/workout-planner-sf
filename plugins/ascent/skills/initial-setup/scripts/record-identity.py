#!/usr/bin/env python3
"""Idempotently record Account and Opportunity identity in a workspace."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


IDENTITY_HEADING = "## Opportunity Identity"
TABLE_HEADER = "| Field | Value |\n| --- | --- |"


def yaml_string(value: str) -> str:
    return yaml.safe_dump(value, default_style='"', allow_unicode=True).strip()


def upsert_yaml_identity(path: Path, account: str, opportunity: str) -> bool:
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    parsed = yaml.safe_load(original) if original.strip() else {}
    if not isinstance(parsed, dict):
        raise ValueError(f"Project identity must be a YAML mapping: {path}")

    updated = original
    for key, value in (("account", account), ("opportunity", opportunity)):
        pattern = re.compile(rf"^{re.escape(key)}\s*:.*$", re.MULTILINE)
        matches = pattern.findall(updated)
        if len(matches) > 1:
            raise ValueError(f"Project identity contains duplicate '{key}' keys: {path}")
        line = f"{key}: {yaml_string(value)}"
        if matches:
            updated = pattern.sub(line, updated, count=1)
        else:
            if updated and not updated.endswith("\n"):
                updated += "\n"
            updated += line + "\n"

    if updated != original:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def overview_row_pattern(label: str) -> re.Pattern[str]:
    return re.compile(
        rf"^[ \t]*\|[ \t]*\*\*{re.escape(label)}\*\*[ \t]*\|[^\r\n]*\|[ \t]*\r?$",
        re.MULTILINE,
    )


def markdown_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def add_missing_rows_to_identity_section(text: str, rows: list[str]) -> str:
    heading_start = text.index(IDENTITY_HEADING)
    content_start = heading_start + len(IDENTITY_HEADING)
    next_heading = re.search(r"^##\s+", text[content_start:], re.MULTILINE)
    section_end = content_start + next_heading.start() if next_heading else len(text)
    section = text[content_start:section_end]
    table_lines = list(re.finditer(r"^\|.*\|\s*$", section, re.MULTILINE))
    if table_lines:
        insertion = content_start + table_lines[-1].end()
        return text[:insertion] + "\n" + "\n".join(rows) + text[insertion:]
    insertion = content_start
    return text[:insertion] + "\n\n" + TABLE_HEADER + "\n" + "\n".join(rows) + text[insertion:]


def upsert_overview_identity(path: Path, account: str, opportunity: str) -> bool:
    original = path.read_text(encoding="utf-8") if path.exists() else "# Project Overview\n"
    updated = original
    missing: list[str] = []
    for label, value in (("Account", account), ("Opportunity", opportunity)):
        pattern = overview_row_pattern(label)
        row = f"| **{label}** | {markdown_value(value)} |"
        if pattern.search(updated):
            updated = pattern.sub(row, updated, count=1)
        else:
            missing.append(row)

    if missing:
        block = f"{IDENTITY_HEADING}\n\n{TABLE_HEADER}\n" + "\n".join(missing) + "\n"
        if IDENTITY_HEADING in updated:
            updated = add_missing_rows_to_identity_section(updated, missing)
        else:
            updated = updated.rstrip() + "\n\n" + block

    if updated != original or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity", required=True, help="Opportunity folder path.")
    parser.add_argument("--account", required=True, help="Confirmed Account name.")
    parser.add_argument("--opportunity-name", required=True, help="Confirmed Opportunity name.")
    args = parser.parse_args()

    root = Path(args.opportunity).expanduser().resolve()
    if not root.is_dir():
        print(f"Opportunity folder does not exist: {root}", file=sys.stderr)
        return 2
    if not args.account.strip() or not args.opportunity_name.strip():
        print("Account and Opportunity names cannot be blank.", file=sys.stderr)
        return 2

    try:
        yaml_changed = upsert_yaml_identity(
            root / "workspace" / ".system" / "project.yaml",
            args.account,
            args.opportunity_name,
        )
        overview_changed = upsert_overview_identity(
            root / "workspace" / "project" / "Project Overview.md",
            args.account,
            args.opportunity_name,
        )
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"Could not record project identity: {error}", file=sys.stderr)
        return 1

    state = "updated" if yaml_changed or overview_changed else "already current"
    print(f"identity {state}: {args.account} / {args.opportunity_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

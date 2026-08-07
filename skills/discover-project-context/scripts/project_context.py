#!/usr/bin/env python3
"""Initialize, update, render, and validate a project-context manifest."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
KINDS = {"local", "slack", "teams", "sharepoint", "web", "other"}
AUTHORITIES = {"canonical", "supporting", "historical"}
SENSITIVITIES = {"public", "internal", "confidential", "restricted"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def paths(root: str) -> tuple[Path, Path, Path]:
    workspace = Path(root).expanduser().resolve()
    context_dir = workspace / ".codex" / "project-context"
    return context_dir, context_dir / "manifest.json", context_dir / "brief.md"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def read_manifest(root: str) -> tuple[Path, dict[str, Any]]:
    _, manifest_path, _ = paths(root)
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("Manifest root must be a JSON object")
    return manifest_path, value


def new_manifest(root: str, name: str | None, objective: str | None) -> dict[str, Any]:
    workspace = Path(root).expanduser().resolve()
    timestamp = now_iso()
    project_name = name or workspace.name
    return {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "id": slugify(project_name),
            "name": project_name,
            "objective": objective or "",
            "current_phase": "",
            "workspace_roots": ["."],
            "technology": [],
            "terms": [],
            "stakeholders": [],
            "constraints": [],
            "updated_at": timestamp,
        },
        "source_policy": {
            "default_freshness_hours": 168,
            "max_excerpt_chars": 1200,
            "max_total_chars": 12000,
            "allow_private_search": False,
        },
        "sources": [],
        "open_questions": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def render_brief(manifest: dict[str, Any]) -> str:
    project = manifest.get("project", {})
    sources = manifest.get("sources", [])
    lines = [
        "# Project Context",
        "",
        f"- Project: {project.get('name') or 'Unknown'} (`{project.get('id') or 'unknown'}`)",
        f"- Objective: {project.get('objective') or 'Unresolved'}",
        f"- Phase: {project.get('current_phase') or 'Unresolved'}",
        f"- Updated: {manifest.get('updated_at') or 'Unknown'}",
        "",
        "## Workspace",
        "",
    ]
    roots = project.get("workspace_roots") or []
    lines.extend(f"- `{root}`" for root in roots)
    if not roots:
        lines.append("- Unresolved")

    for heading, key in (
        ("Technology", "technology"),
        ("Terms", "terms"),
        ("Stakeholders", "stakeholders"),
        ("Constraints", "constraints"),
    ):
        values = project.get(key) or []
        if values:
            lines.extend(["", f"## {heading}", ""])
            lines.extend(f"- {value}" for value in values)

    lines.extend(["", "## Canonical Sources", ""])
    if sources:
        lines.extend([
            "| Priority | Kind | Source | Purpose |",
            "| ---: | --- | --- | --- |",
        ])
        for source in sorted(sources, key=lambda item: (-int(item.get("priority", 0)), item.get("id", ""))):
            status = "" if source.get("enabled", True) else " (disabled)"
            locator = str(source.get("locator", "")).replace("|", "\\|")
            purpose = str(source.get("purpose", "")).replace("|", "\\|")
            label = str(source.get("label", source.get("id", "source"))).replace("|", "\\|")
            lines.append(
                f"| {source.get('priority', '')} | {source.get('kind', '')} | "
                f"{label}{status}: `{locator}` | {purpose} |"
            )
    else:
        lines.append("No sources recorded yet.")

    lines.extend(["", "## Open Questions", ""])
    questions = manifest.get("open_questions") or []
    lines.extend(f"- {question}" for question in questions)
    if not questions:
        lines.append("- None")

    lines.extend([
        "",
        "## Usage",
        "",
        "Read this brief and `manifest.json` before exploratory project searches. Use the recorded source purpose, priority, filters, and query hints to keep retrieval narrow.",
        "",
    ])
    return "\n".join(lines)


def validate_manifest(manifest: dict[str, Any], allow_incomplete: bool = False) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")

    project = manifest.get("project")
    if not isinstance(project, dict):
        errors.append("project must be an object")
        project = {}
    for field in ("id", "name", "objective", "current_phase"):
        if not isinstance(project.get(field), str):
            errors.append(f"project.{field} must be a string")
        elif not allow_incomplete and not project.get(field).strip():
            errors.append(f"project.{field} must not be empty")
    if project.get("id") and slugify(project["id"]) != project["id"]:
        errors.append("project.id must be a lowercase slug")
    for field in ("workspace_roots", "technology", "terms", "stakeholders", "constraints"):
        if not isinstance(project.get(field), list) or not all(isinstance(item, str) for item in project.get(field, [])):
            errors.append(f"project.{field} must be an array of strings")

    policy = manifest.get("source_policy")
    if not isinstance(policy, dict):
        errors.append("source_policy must be an object")
        policy = {}
    for field in ("default_freshness_hours", "max_excerpt_chars", "max_total_chars"):
        if not isinstance(policy.get(field), int) or policy.get(field, -1) < 0:
            errors.append(f"source_policy.{field} must be a non-negative integer")
    if not isinstance(policy.get("allow_private_search"), bool):
        errors.append("source_policy.allow_private_search must be a boolean")

    sources = manifest.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be an array")
        sources = []
    if not allow_incomplete and not sources:
        errors.append("sources must contain at least one canonical project source")
    seen: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id or slugify(source_id) != source_id:
            errors.append(f"{prefix}.id must be a lowercase slug")
        elif source_id in seen:
            errors.append(f"{prefix}.id duplicates {source_id}")
        else:
            seen.add(source_id)
        if source.get("kind") not in KINDS:
            errors.append(f"{prefix}.kind must be one of {sorted(KINDS)}")
        for field in ("label", "locator", "purpose"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if source.get("authority") not in AUTHORITIES:
            errors.append(f"{prefix}.authority must be one of {sorted(AUTHORITIES)}")
        priority = source.get("priority")
        if not isinstance(priority, int) or not 1 <= priority <= 5:
            errors.append(f"{prefix}.priority must be an integer from 1 to 5")
        if source.get("sensitivity") not in SENSITIVITIES:
            errors.append(f"{prefix}.sensitivity must be one of {sorted(SENSITIVITIES)}")
        if not isinstance(source.get("enabled"), bool):
            errors.append(f"{prefix}.enabled must be a boolean")
        for field in ("query_hints", "include", "exclude"):
            if not isinstance(source.get(field), list) or not all(isinstance(item, str) for item in source.get(field, [])):
                errors.append(f"{prefix}.{field} must be an array of strings")
        window = source.get("time_window")
        if not isinstance(window, dict) or set(window) != {"start", "end"}:
            errors.append(f"{prefix}.time_window must contain exactly start and end")
        freshness = source.get("freshness_hours")
        if not isinstance(freshness, int) or freshness < 0:
            errors.append(f"{prefix}.freshness_hours must be a non-negative integer")

    if not isinstance(manifest.get("open_questions"), list) or not all(
        isinstance(item, str) for item in manifest.get("open_questions", [])
    ):
        errors.append("open_questions must be an array of strings")
    return errors


def command_init(args: argparse.Namespace) -> None:
    context_dir, manifest_path, brief_path = paths(args.root)
    if manifest_path.exists() and not args.force:
        print(f"Existing manifest preserved: {manifest_path}")
        return
    context_dir.mkdir(parents=True, exist_ok=True)
    ignore_path = context_dir / ".gitignore"
    if not ignore_path.exists():
        atomic_write(ignore_path, "*\n!.gitignore\n")
    manifest = new_manifest(args.root, args.name, args.objective)
    write_json(manifest_path, manifest)
    atomic_write(brief_path, render_brief(manifest))
    print(f"Initialized {manifest_path}")


def command_set_project(args: argparse.Namespace) -> None:
    manifest_path, manifest = read_manifest(args.root)
    project = manifest["project"]
    mapping = {
        "name": args.name,
        "objective": args.objective,
        "current_phase": args.phase,
    }
    for field, value in mapping.items():
        if value is not None:
            project[field] = value
    if args.project_id is not None:
        project["id"] = slugify(args.project_id)
    for field, value in (
        ("workspace_roots", args.workspace_root),
        ("technology", args.technology),
        ("terms", args.term),
        ("stakeholders", args.stakeholder),
        ("constraints", args.constraint),
    ):
        if value is not None:
            project[field] = value
    timestamp = now_iso()
    project["updated_at"] = timestamp
    manifest["updated_at"] = timestamp
    write_json(manifest_path, manifest)
    print(f"Updated project metadata in {manifest_path}")


def command_upsert_source(args: argparse.Namespace) -> None:
    manifest_path, manifest = read_manifest(args.root)
    timestamp = now_iso()
    source = {
        "id": slugify(args.id),
        "kind": args.kind,
        "label": args.label,
        "locator": args.locator,
        "purpose": args.purpose,
        "authority": args.authority,
        "priority": args.priority,
        "query_hints": args.query_hint or [],
        "include": args.include or [],
        "exclude": args.exclude or [],
        "time_window": {"start": args.start, "end": args.end},
        "freshness_hours": args.freshness_hours,
        "sensitivity": args.sensitivity,
        "enabled": not args.disabled,
        "last_confirmed_at": timestamp,
    }
    sources = manifest.setdefault("sources", [])
    for index, existing in enumerate(sources):
        if existing.get("id") == source["id"]:
            sources[index] = source
            break
    else:
        sources.append(source)
    manifest["updated_at"] = timestamp
    manifest["project"]["updated_at"] = timestamp
    write_json(manifest_path, manifest)
    print(f"Upserted source {source['id']} in {manifest_path}")


def command_render(args: argparse.Namespace) -> None:
    _, manifest = read_manifest(args.root)
    _, _, brief_path = paths(args.root)
    atomic_write(brief_path, render_brief(manifest))
    print(f"Rendered {brief_path}")


def command_validate(args: argparse.Namespace) -> None:
    manifest_path, manifest = read_manifest(args.root)
    errors = validate_manifest(manifest, allow_incomplete=args.allow_incomplete)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Valid project context manifest: {manifest_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize the project context store")
    init_parser.add_argument("--root", default=".")
    init_parser.add_argument("--name")
    init_parser.add_argument("--objective")
    init_parser.add_argument("--force", action="store_true", help="Replace an existing manifest")
    init_parser.set_defaults(func=command_init)

    project_parser = subparsers.add_parser("set-project", help="Update project metadata")
    project_parser.add_argument("--root", default=".")
    project_parser.add_argument("--id", dest="project_id")
    project_parser.add_argument("--name")
    project_parser.add_argument("--objective")
    project_parser.add_argument("--phase")
    project_parser.add_argument("--workspace-root", action="append")
    project_parser.add_argument("--technology", action="append")
    project_parser.add_argument("--term", action="append")
    project_parser.add_argument("--stakeholder", action="append")
    project_parser.add_argument("--constraint", action="append")
    project_parser.set_defaults(func=command_set_project)

    source_parser = subparsers.add_parser("upsert-source", help="Add or replace a source by ID")
    source_parser.add_argument("--root", default=".")
    source_parser.add_argument("--id", required=True)
    source_parser.add_argument("--kind", choices=sorted(KINDS), required=True)
    source_parser.add_argument("--label", required=True)
    source_parser.add_argument("--locator", required=True)
    source_parser.add_argument("--purpose", required=True)
    source_parser.add_argument("--authority", choices=sorted(AUTHORITIES), default="supporting")
    source_parser.add_argument("--priority", type=int, choices=range(1, 6), default=3)
    source_parser.add_argument("--query-hint", action="append")
    source_parser.add_argument("--include", action="append")
    source_parser.add_argument("--exclude", action="append")
    source_parser.add_argument("--start")
    source_parser.add_argument("--end")
    source_parser.add_argument("--freshness-hours", type=int, default=168)
    source_parser.add_argument("--sensitivity", choices=sorted(SENSITIVITIES), default="internal")
    source_parser.add_argument("--disabled", action="store_true")
    source_parser.set_defaults(func=command_upsert_source)

    render_parser = subparsers.add_parser("render-brief", help="Render brief.md from the manifest")
    render_parser.add_argument("--root", default=".")
    render_parser.set_defaults(func=command_render)

    validate_parser = subparsers.add_parser("validate", help="Validate the manifest")
    validate_parser.add_argument("--root", default=".")
    validate_parser.add_argument("--allow-incomplete", action="store_true")
    validate_parser.set_defaults(func=command_validate)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

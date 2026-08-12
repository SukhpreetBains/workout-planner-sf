#!/usr/bin/env python3
"""Initialize, update, render, and validate a project-context manifest."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
KINDS = {"local", "slack", "teams", "sharepoint", "web", "other"}
AUTHORITIES = {"canonical", "supporting", "historical"}
SENSITIVITIES = {"public", "internal", "confidential", "restricted"}
ACCESS_STATES = {"available", "unavailable", "unknown"}
DISCOVERY_SYSTEMS = {"local", "chat", "document", "other"}
DEFAULT_EXPLORATION_CAPS = {
    "local": 30,
    "chat": 30,
    "document": 30,
    "other": 10,
}
DEFAULT_ACCESS_REASONS = {
    "available": "Access confirmed during discovery.",
    "unavailable": "Access was not available during discovery.",
    "unknown": "Access was not verified during discovery.",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def paths(root: str) -> tuple[Path, Path, Path]:
    workspace = Path(root).expanduser().resolve()
    context_dir = workspace / ".codex" / "project-context"
    return context_dir, context_dir / "manifest.json", context_dir / "brief.md"


def source_context_tool() -> Path:
    return Path(__file__).resolve().parents[2] / "initial-setup" / "scripts" / "manage-source-context.py"


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
        "source_context": {
            "path": "Agent Inbox/source-context.yaml",
            "last_imported_at": None,
            "source_count": 0,
        },
        "discovery_runs": [],
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

    shared = manifest.get("source_context") or {}
    if shared:
        lines.extend([
            "",
            "## Shared Source Record",
            "",
            f"- Path: `{shared.get('path', 'Agent Inbox/source-context.yaml')}`",
            f"- Last imported: {shared.get('last_imported_at') or 'Not imported'}",
            f"- Shared references imported: {shared.get('source_count', 0)}",
        ])

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
            "| Priority | Kind | Access | Source | Purpose |",
            "| ---: | --- | --- | --- | --- |",
        ])
        for source in sorted(sources, key=lambda item: (-int(item.get("priority", 0)), item.get("id", ""))):
            status = "" if source.get("enabled", True) else " (disabled)"
            locator = str(source.get("locator", "")).replace("|", "\\|")
            purpose = str(source.get("purpose", "")).replace("|", "\\|")
            label = str(source.get("label", source.get("id", "source"))).replace("|", "\\|")
            access = source.get("access") or {"state": "available", "reason": "Legacy manifest; access state not recorded."}
            access_state = str(access.get("state", "unknown"))
            lines.append(
                f"| {source.get('priority', '')} | {source.get('kind', '')} | {access_state} | "
                f"{label}{status}: `{locator}` | {purpose} |"
            )
    else:
        lines.append("No sources recorded yet.")

    lines.extend(["", "## Open Questions", ""])
    questions = manifest.get("open_questions") or []
    lines.extend(f"- {question}" for question in questions)
    if not questions:
        lines.append("- None")

    discovery_runs = manifest.get("discovery_runs") or []
    if discovery_runs:
        latest_run = discovery_runs[-1]
        lines.extend([
            "",
            "## Latest Discovery Measurement",
            "",
            f"- Recorded: {latest_run.get('recorded_at', 'Unknown')}",
            f"- Sources considered/recorded: {latest_run.get('sources_considered', '?')}/{latest_run.get('sources_recorded', '?')}",
            f"- Connector calls: {latest_run.get('connector_calls', '?')}; items inspected: {latest_run.get('items_inspected', '?')}",
            f"- Inspected characters: {latest_run.get('characters_inspected', '?')}; estimated tokens: {latest_run.get('estimated_tokens', '?')}",
        ])

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
        access = source.get("access")
        if access is not None:
            if not isinstance(access, dict):
                errors.append(f"{prefix}.access must be an object")
            else:
                if access.get("state") not in ACCESS_STATES:
                    errors.append(f"{prefix}.access.state must be one of {sorted(ACCESS_STATES)}")
                reason = access.get("reason")
                if not isinstance(reason, str) or not reason.strip() or len(reason) > 240 or "\n" in reason:
                    errors.append(f"{prefix}.access.reason must be a short single-line string of at most 240 characters")
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

    source_context = manifest.get("source_context")
    if source_context is not None:
        if not isinstance(source_context, dict):
            errors.append("source_context must be an object")
        else:
            if not isinstance(source_context.get("path"), str) or not source_context["path"].strip():
                errors.append("source_context.path must be a non-empty string")
            imported_at = source_context.get("last_imported_at")
            if imported_at is not None and not isinstance(imported_at, str):
                errors.append("source_context.last_imported_at must be a string or null")
            if not isinstance(source_context.get("source_count", 0), int) or source_context.get("source_count", -1) < 0:
                errors.append("source_context.source_count must be a non-negative integer")

    if not isinstance(manifest.get("open_questions"), list) or not all(
        isinstance(item, str) for item in manifest.get("open_questions", [])
    ):
        errors.append("open_questions must be an array of strings")
    discovery_runs = manifest.get("discovery_runs", [])
    if not isinstance(discovery_runs, list):
        errors.append("discovery_runs must be an array")
    else:
        numeric_fields = (
            "sources_considered",
            "sources_recorded",
            "connector_calls",
            "items_inspected",
            "characters_inspected",
            "estimated_tokens",
        )
        for index, run in enumerate(discovery_runs):
            prefix = f"discovery_runs[{index}]"
            if not isinstance(run, dict):
                errors.append(f"{prefix} must be an object")
                continue
            if not isinstance(run.get("recorded_at"), str) or not run["recorded_at"].strip():
                errors.append(f"{prefix}.recorded_at must be a non-empty string")
            for field in numeric_fields:
                if not isinstance(run.get(field), int) or run[field] < 0:
                    errors.append(f"{prefix}.{field} must be a non-negative integer")
            caps = run.get("exploration_caps")
            if caps is not None and not isinstance(caps, dict):
                errors.append(f"{prefix}.exploration_caps must be an object")
            elif isinstance(caps, dict):
                for system, cap in caps.items():
                    if system not in DISCOVERY_SYSTEMS:
                        errors.append(f"{prefix}.exploration_caps contains unknown system {system}")
                    if not isinstance(cap, int) or cap < 1:
                        errors.append(f"{prefix}.exploration_caps.{system} must be a positive integer")
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
        "access": {
            "state": args.access_state,
            "reason": args.access_reason or DEFAULT_ACCESS_REASONS[args.access_state],
        },
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


def command_set_source_access(args: argparse.Namespace) -> None:
    manifest_path, manifest = read_manifest(args.root)
    for source in manifest.get("sources", []):
        if source.get("id") == args.id:
            source["access"] = {
                "state": args.access_state,
                "reason": args.access_reason or DEFAULT_ACCESS_REASONS[args.access_state],
            }
            timestamp = now_iso()
            source["last_confirmed_at"] = timestamp
            manifest["updated_at"] = timestamp
            write_json(manifest_path, manifest)
            print(f"Updated access for source {args.id} in {manifest_path}")
            return
    raise SystemExit(f"Source not found: {args.id}")


def parse_caps(values: list[str] | None) -> dict[str, int]:
    caps = dict(DEFAULT_EXPLORATION_CAPS)
    for value in values or []:
        if "=" not in value:
            raise SystemExit("--cap must use SYSTEM=COUNT")
        system, raw_count = value.split("=", 1)
        if system not in DISCOVERY_SYSTEMS:
            raise SystemExit(f"Unknown discovery system for --cap: {system}")
        try:
            count = int(raw_count)
        except ValueError as exc:
            raise SystemExit(f"Discovery cap must be an integer: {value}") from exc
        if count < 1:
            raise SystemExit("Discovery caps must be positive")
        caps[system] = count
    return caps


def command_record_discovery(args: argparse.Namespace) -> None:
    manifest_path, manifest = read_manifest(args.root)
    values = (
        args.sources_considered,
        args.sources_recorded,
        args.connector_calls,
        args.items_inspected,
        args.characters_inspected,
    )
    if any(value < 0 for value in values) or (args.estimated_tokens is not None and args.estimated_tokens < 0):
        raise SystemExit("Discovery measurements must be non-negative")
    if args.sources_recorded > args.sources_considered:
        raise SystemExit("--sources-recorded cannot exceed --sources-considered")
    estimated_tokens = args.estimated_tokens
    if estimated_tokens is None:
        estimated_tokens = math.ceil(args.characters_inspected / 4)
    run = {
        "recorded_at": now_iso(),
        "sources_considered": args.sources_considered,
        "sources_recorded": args.sources_recorded,
        "connector_calls": args.connector_calls,
        "items_inspected": args.items_inspected,
        "characters_inspected": args.characters_inspected,
        "estimated_tokens": estimated_tokens,
        "exploration_caps": parse_caps(args.cap),
    }
    runs = manifest.setdefault("discovery_runs", [])
    if not isinstance(runs, list):
        raise SystemExit("discovery_runs must be an array")
    runs.append(run)
    manifest["discovery_runs"] = runs[-20:]
    manifest["updated_at"] = run["recorded_at"]
    write_json(manifest_path, manifest)
    print(f"Recorded discovery estimate of {estimated_tokens} tokens in {manifest_path}")


def command_import_source_context(args: argparse.Namespace) -> None:
    manifest_path, manifest = read_manifest(args.root)
    tool = source_context_tool()
    if not tool.is_file():
        raise SystemExit(f"Initial setup source-context manager not found: {tool}")
    command = [sys.executable, str(tool), "export", "--root", args.root]
    if args.file:
        command.extend(["--file", args.file])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "Unable to export project communications record")
    try:
        exported = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid source-context export: {exc}") from exc
    imported_sources = exported.get("sources")
    if not isinstance(imported_sources, list):
        raise SystemExit("Source-context export did not contain a sources array")
    sources = manifest.setdefault("sources", [])
    existing = {source.get("id"): index for index, source in enumerate(sources) if isinstance(source, dict)}
    for source in imported_sources:
        if not isinstance(source, dict) or not source.get("id"):
            raise SystemExit("Source-context export contained an invalid source")
        source_id = source["id"]
        if source_id in existing:
            sources[existing[source_id]] = source
        else:
            existing[source_id] = len(sources)
            sources.append(source)
    timestamp = now_iso()
    workspace = Path(args.root).expanduser().resolve()
    exported_path = Path(str(exported.get("path", ""))).expanduser().resolve()
    try:
        recorded_path = str(exported_path.relative_to(workspace))
    except ValueError:
        recorded_path = str(exported_path)
    manifest["source_context"] = {
        "path": recorded_path,
        "last_imported_at": timestamp,
        "source_count": len(imported_sources),
    }
    manifest["updated_at"] = timestamp
    manifest["project"]["updated_at"] = timestamp
    errors = validate_manifest(manifest, allow_incomplete=args.allow_incomplete)
    if errors:
        raise SystemExit("Imported source context produced an invalid manifest: " + "; ".join(errors))
    write_json(manifest_path, manifest)
    _, _, brief_path = paths(args.root)
    atomic_write(brief_path, render_brief(manifest))
    print(f"Imported {len(imported_sources)} shared source references into {manifest_path}")


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
    source_parser.add_argument("--access-state", choices=sorted(ACCESS_STATES), default="unknown")
    source_parser.add_argument("--access-reason")
    source_parser.add_argument("--disabled", action="store_true")
    source_parser.set_defaults(func=command_upsert_source)

    render_parser = subparsers.add_parser("render-brief", help="Render brief.md from the manifest")
    render_parser.add_argument("--root", default=".")
    render_parser.set_defaults(func=command_render)

    access_parser = subparsers.add_parser("set-source-access", help="Record a bounded source access state")
    access_parser.add_argument("--root", default=".")
    access_parser.add_argument("--id", required=True)
    access_parser.add_argument("--access-state", choices=sorted(ACCESS_STATES), required=True)
    access_parser.add_argument("--access-reason")
    access_parser.set_defaults(func=command_set_source_access)

    discovery_parser = subparsers.add_parser("record-discovery", help="Record lightweight discovery measurements")
    discovery_parser.add_argument("--root", default=".")
    discovery_parser.add_argument("--sources-considered", type=int, required=True)
    discovery_parser.add_argument("--sources-recorded", type=int, required=True)
    discovery_parser.add_argument("--connector-calls", type=int, required=True)
    discovery_parser.add_argument("--items-inspected", type=int, required=True)
    discovery_parser.add_argument("--characters-inspected", type=int, required=True)
    discovery_parser.add_argument("--estimated-tokens", type=int)
    discovery_parser.add_argument("--cap", action="append", help="Override a system cap using SYSTEM=COUNT")
    discovery_parser.set_defaults(func=command_record_discovery)

    import_parser = subparsers.add_parser("import-source-context", help="Import the setup-generated project communications record")
    import_parser.add_argument("--root", default=".")
    import_parser.add_argument("--file")
    import_parser.add_argument("--allow-incomplete", action="store_true")
    import_parser.set_defaults(func=command_import_source_context)

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

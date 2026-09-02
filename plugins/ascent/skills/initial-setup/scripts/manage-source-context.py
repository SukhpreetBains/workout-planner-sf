#!/usr/bin/env python3
"""Initialize, validate, update, and export the shared source-context YAML."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


KINDS = {"local", "slack", "teams", "sharepoint", "web", "other"}
ACCESS_STATES = {"available", "unavailable", "unknown"}
AUTHORITIES = {"canonical", "supporting", "historical"}
SENSITIVITIES = {"public", "internal", "confidential", "restricted"}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "source"


def context_path(root: str, explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return Path(root).expanduser().resolve() / "workspace" / ".system" / "source-context.yaml"


def scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "~"}:
        return None
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value in {"true", "false"}:
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value.startswith('"'):
        return json.loads(value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def fallback_yaml_load(text: str) -> dict[str, Any]:
    """Parse the small mapping/list YAML subset emitted by this script."""
    tokens: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise ValueError(f"Tabs are not supported at line {number}")
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ValueError(f"Indentation must use two spaces at line {number}")
        tokens.append((indent, raw.strip()))

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(tokens) or tokens[index][0] != indent:
            return {}, index
        is_list = tokens[index][1].startswith("- ")
        container: Any = [] if is_list else {}
        while index < len(tokens) and tokens[index][0] == indent:
            content = tokens[index][1]
            if is_list:
                if not content.startswith("- "):
                    raise ValueError("Cannot mix list and mapping entries")
                body = content[2:].strip()
                if not body:
                    item, index = parse_block(index + 1, indent + 2)
                    container.append(item)
                    continue
                if ":" not in body:
                    container.append(scalar(body))
                    index += 1
                    continue
                key, raw_value = body.split(":", 1)
                item: dict[str, Any] = {}
                item[key.strip()] = scalar(raw_value) if raw_value.strip() else None
                index += 1
                while index < len(tokens) and tokens[index][0] == indent + 2 and not tokens[index][1].startswith("- "):
                    child_key, child_value = tokens[index][1].split(":", 1)
                    if child_value.strip():
                        item[child_key.strip()] = scalar(child_value)
                        index += 1
                    else:
                        value, index = parse_block(index + 1, indent + 4)
                        item[child_key.strip()] = value
                container.append(item)
            else:
                if content.startswith("- ") or ":" not in content:
                    raise ValueError("Invalid mapping entry")
                key, raw_value = content.split(":", 1)
                if raw_value.strip():
                    container[key.strip()] = scalar(raw_value)
                    index += 1
                else:
                    value, index = parse_block(index + 1, indent + 2)
                    container[key.strip()] = value
        return container, index

    parsed, consumed = parse_block(0, 0)
    if consumed != len(tokens) or not isinstance(parsed, dict):
        raise ValueError("Unable to parse source-context YAML")
    return parsed


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"Unable to read {path}: {exc}") from exc
    try:
        try:
            import yaml  # type: ignore
        except ImportError:
            value = fallback_yaml_load(text)
        else:
            value = yaml.safe_load(text)
    except Exception as exc:
        raise SystemExit(f"Unable to parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a YAML mapping in {path}")
    return value


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def dump_yaml(value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        if not value:
            return [prefix + "{}"]
        lines: list[str] = []
        for key, child in value.items():
            if isinstance(child, (dict, list)) and child:
                lines.append(f"{prefix}{key}:")
                lines.extend(dump_yaml(child, indent + 2))
            elif isinstance(child, list):
                lines.append(f"{prefix}{key}: []")
            elif isinstance(child, dict):
                lines.append(f"{prefix}{key}: {{}}")
            else:
                lines.append(f"{prefix}{key}: {yaml_scalar(child)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [prefix + "[]"]
        lines = []
        for item in value:
            if isinstance(item, dict):
                pairs = list(item.items())
                if not pairs:
                    lines.append(prefix + "- {}")
                    continue
                first_key, first_value = pairs[0]
                if isinstance(first_value, (dict, list)) and first_value:
                    lines.append(f"{prefix}- {first_key}:")
                    lines.extend(dump_yaml(first_value, indent + 4))
                else:
                    rendered = "[]" if first_value == [] else "{}" if first_value == {} else yaml_scalar(first_value)
                    lines.append(f"{prefix}- {first_key}: {rendered}")
                for key, child in pairs[1:]:
                    child_prefix = " " * (indent + 2)
                    if isinstance(child, (dict, list)) and child:
                        lines.append(f"{child_prefix}{key}:")
                        lines.extend(dump_yaml(child, indent + 4))
                    elif isinstance(child, list):
                        lines.append(f"{child_prefix}{key}: []")
                    elif isinstance(child, dict):
                        lines.append(f"{child_prefix}{key}: {{}}")
                    else:
                        lines.append(f"{child_prefix}{key}: {yaml_scalar(child)}")
            else:
                lines.append(f"{prefix}- {yaml_scalar(item)}")
        return lines
    return [prefix + yaml_scalar(value)]


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(dump_yaml(value)) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def default_record(account: str, opportunity: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "account": account,
        "opportunity": opportunity,
        "last_verified": date.today().isoformat(),
        "sharepoint_locations": [],
        "messaging_platforms": [],
        "project_sources": [],
    }


def access_from(location: dict[str, Any], connection_state: str | None = None) -> dict[str, str]:
    access = location.get("access")
    if isinstance(access, dict) and access.get("state") in ACCESS_STATES:
        return {
            "state": str(access["state"]),
            "reason": str(access.get("reason") or "Access state was recorded without additional detail."),
        }
    status = str(location.get("status", "scope_not_verified"))
    if status == "confirmed" and connection_state in {None, "usable"}:
        return {"state": "available", "reason": "Location was confirmed in the project communications record."}
    if connection_state == "not connected":
        return {"state": "unavailable", "reason": "The source connector was not connected during setup."}
    return {"state": "unknown", "reason": "Source scope was not verified during setup."}


def locator_from(kind: str, location: dict[str, Any], platform: str = "") -> str:
    if location.get("locator"):
        return str(location["locator"])
    identifiers = location.get("identifiers") if isinstance(location.get("identifiers"), dict) else {}
    if kind == "sharepoint":
        hostname = identifiers.get("hostname", "")
        site_path = identifiers.get("site_path", "")
        folder_path = identifiers.get("folder_path", "")
        if hostname:
            return f"https://{hostname}{site_path}/{folder_path}".rstrip("/")
    parent_id = identifiers.get("parent_id") or identifiers.get("team_id") or ""
    channel_id = identifiers.get("channel_id") or ""
    if channel_id:
        return f"{kind}://{parent_id}/{channel_id}".rstrip("/")
    parent = location.get("parent_name", "")
    name = location.get("name", "source")
    return f"{platform or kind}:{parent}/{name}".rstrip("/")


def normalize_location(kind: str, location: dict[str, Any], platform: str = "", connection_state: str | None = None) -> dict[str, Any]:
    name = str(location.get("name") or location.get("label") or "Source")
    source_id = slugify(str(location.get("id") or f"{kind}-{name}"))
    return {
        "id": source_id,
        "kind": kind,
        "label": name,
        "locator": locator_from(kind, location, platform),
        "purpose": str(location.get("purpose") or location.get("description") or f"Confirmed {kind} project context"),
        "authority": location.get("authority", "supporting"),
        "priority": int(location.get("priority", 3)),
        "query_hints": location.get("query_hints", []),
        "include": location.get("include", []),
        "exclude": location.get("exclude", []),
        "time_window": location.get("time_window", {"start": None, "end": None}),
        "freshness_hours": int(location.get("freshness_hours", 168)),
        "sensitivity": location.get("sensitivity", "internal"),
        "enabled": bool(location.get("enabled", True)),
        "access": access_from(location, connection_state),
        "last_confirmed_at": str(location.get("last_confirmed_at") or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")),
    }


def exported_sources(record: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for location in record.get("sharepoint_locations", []) or []:
        if isinstance(location, dict):
            sources.append(normalize_location("sharepoint", location))
    for platform in record.get("messaging_platforms", []) or []:
        if not isinstance(platform, dict):
            continue
        platform_name = str(platform.get("name", "other"))
        lowered = platform_name.lower()
        kind = "slack" if "slack" in lowered else "teams" if "team" in lowered else "other"
        connection_state = str(platform.get("connection_state", "authenticated—scope not verified"))
        for location in platform.get("locations", []) or []:
            if isinstance(location, dict):
                sources.append(normalize_location(kind, location, platform_name, connection_state))
    for location in record.get("project_sources", []) or []:
        if isinstance(location, dict):
            kind = str(location.get("kind", "other"))
            sources.append(normalize_location(kind if kind in KINDS else "other", location))
    return sources


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version", 1) != 1:
        errors.append("schema_version must equal 1")
    for field in ("account", "opportunity", "last_verified"):
        if not isinstance(record.get(field), (str, date, datetime)) or not str(record.get(field)).strip():
            errors.append(f"{field} must be a non-empty string")
    for field in ("sharepoint_locations", "messaging_platforms", "project_sources"):
        if field in record and not isinstance(record[field], list):
            errors.append(f"{field} must be an array")
    seen: set[str] = set()
    for source in exported_sources(record):
        source_id = source["id"]
        if source_id in seen:
            errors.append(f"duplicate source id: {source_id}")
        seen.add(source_id)
        if not source["locator"]:
            errors.append(f"source {source_id} must have a locator or resolvable identifiers")
        if source["authority"] not in AUTHORITIES:
            errors.append(f"source {source_id} has invalid authority")
        if not 1 <= source["priority"] <= 5:
            errors.append(f"source {source_id} priority must be from 1 to 5")
        if source["sensitivity"] not in SENSITIVITIES:
            errors.append(f"source {source_id} has invalid sensitivity")
    return errors


def parse_identifiers(values: list[str] | None) -> dict[str, str]:
    identifiers: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise SystemExit("--identifier must use KEY=VALUE")
        key, item = value.split("=", 1)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise SystemExit(f"Invalid identifier key: {key}")
        identifiers[key] = item
    return identifiers


def location_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "id": slugify(args.id),
        "name": args.name,
        "parent_name": args.parent_name,
        "locator": args.locator,
        "identifiers": parse_identifiers(args.identifier),
        "description": args.description,
        "purpose": args.purpose,
        "status": args.status,
        "authority": args.authority,
        "priority": args.priority,
        "query_hints": args.query_hint or [],
        "include": args.include or [],
        "exclude": args.exclude or [],
        "time_window": {"start": args.start, "end": args.end},
        "freshness_hours": args.freshness_hours,
        "sensitivity": args.sensitivity,
        "enabled": not args.disabled,
        "access": {"state": args.access_state, "reason": args.access_reason},
        "last_confirmed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def upsert(items: list[dict[str, Any]], location: dict[str, Any]) -> None:
    for index, existing in enumerate(items):
        if isinstance(existing, dict) and slugify(str(existing.get("id", ""))) == location["id"]:
            items[index] = location
            return
    items.append(location)


def command_init(args: argparse.Namespace) -> None:
    path = context_path(args.root, args.file)
    if path.exists() and not args.force:
        print(f"Existing project communications record preserved: {path}")
        return
    atomic_write(path, default_record(args.account, args.opportunity))
    print(f"Initialized project communications record: {path}")


def command_validate(args: argparse.Namespace) -> None:
    path = context_path(args.root, args.file)
    errors = validate(load_yaml(path))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Valid project communications record: {path}")


def command_export(args: argparse.Namespace) -> None:
    path = context_path(args.root, args.file)
    record = load_yaml(path)
    errors = validate(record)
    if errors:
        raise SystemExit("Invalid project communications record: " + "; ".join(errors))
    print(json.dumps({"path": str(path), "sources": exported_sources(record)}, ensure_ascii=False))


def command_upsert(args: argparse.Namespace) -> None:
    path = context_path(args.root, args.file)
    record = load_yaml(path)
    location = location_from_args(args)
    if args.kind in {"slack", "teams"}:
        platform_name = args.platform_name or ("Slack" if args.kind == "slack" else "Microsoft Teams")
        platforms = record.setdefault("messaging_platforms", [])
        platform = next((item for item in platforms if isinstance(item, dict) and str(item.get("name", "")).lower() == platform_name.lower()), None)
        if platform is None:
            platform = {"name": platform_name, "connection_state": args.connection_state, "locations": []}
            platforms.append(platform)
        platform["connection_state"] = args.connection_state
        locations = platform.setdefault("locations", [])
        upsert(locations, location)
    elif args.kind == "sharepoint":
        upsert(record.setdefault("sharepoint_locations", []), location)
    else:
        location["kind"] = args.kind
        upsert(record.setdefault("project_sources", []), location)
    record["last_verified"] = date.today().isoformat()
    errors = validate(record)
    if errors:
        raise SystemExit("Refusing to write invalid project communications record: " + "; ".join(errors))
    atomic_write(path, record)
    print(f"Upserted {location['id']} in project communications record: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "export"):
        child = subparsers.add_parser(name)
        child.add_argument("--root", default=".")
        child.add_argument("--file")
        child.set_defaults(func=command_validate if name == "validate" else command_export)
    init = subparsers.add_parser("init")
    init.add_argument("--root", default=".")
    init.add_argument("--file")
    init.add_argument("--account", required=True)
    init.add_argument("--opportunity", required=True)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)
    source = subparsers.add_parser("upsert-source")
    source.add_argument("--root", default=".")
    source.add_argument("--file")
    source.add_argument("--id", required=True)
    source.add_argument("--kind", choices=sorted(KINDS), required=True)
    source.add_argument("--name", required=True)
    source.add_argument("--parent-name")
    source.add_argument("--locator", required=True)
    source.add_argument("--identifier", action="append")
    source.add_argument("--description", default="")
    source.add_argument("--purpose", required=True)
    source.add_argument("--status", choices=("confirmed", "scope_not_verified"), default="confirmed")
    source.add_argument("--authority", choices=sorted(AUTHORITIES), default="supporting")
    source.add_argument("--priority", type=int, choices=range(1, 6), default=3)
    source.add_argument("--query-hint", action="append")
    source.add_argument("--include", action="append")
    source.add_argument("--exclude", action="append")
    source.add_argument("--start")
    source.add_argument("--end")
    source.add_argument("--freshness-hours", type=int, default=168)
    source.add_argument("--sensitivity", choices=sorted(SENSITIVITIES), default="internal")
    source.add_argument("--access-state", choices=sorted(ACCESS_STATES), default="available")
    source.add_argument("--access-reason", default="Location was confirmed for project context retrieval.")
    source.add_argument("--disabled", action="store_true")
    source.add_argument("--platform-name")
    source.add_argument("--connection-state", choices=("usable", "authenticated—scope not verified", "not connected", "not yet supported"), default="usable")
    source.set_defaults(func=command_upsert)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Plan, write, and record source collection for workspace-collect.

Every command prints JSON.

  plan        List the sources marked `collect: true` in source-context.yaml,
              with each source's cursor. These are the only sources a
              collection run may read. `--since` starts missing cursors.
  write       Render collected items from a JSON file into new inbox files,
              then advance that source's cursor. Never overwrites a file.
  fail        Record that a source could not be read. Its cursor is unchanged.
  schedule    Record the host schedule and start missing cursors at now, so the
              first scheduled run collects only material that arrives later.
  unschedule  Remove the recorded schedule. Cursors are kept.
  status      Schedule, last results, and collected files still in the inbox.

Inbox files are written as hidden `.partial` files and then renamed, so
workspace-add's batch selector (which ignores hidden files) never reads a
half-written file. Each file starts with front matter carrying
`collected_by: workspace-collect`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import (  # noqa: E402
    COLLECTED_BY,
    COLLECTION_FILE,
    COLLECTION_STATE_FILE,
    INBOX,
    SOURCE_CONTEXT_FILE,
    rel,
)

SYSTEMS = {"slack": "Slack", "microsoft-teams": "Microsoft Teams"}
LOCATION_TYPES = {"channel", "thread", "meeting_series"}
SEEN_LIMIT = 500


# ---- time ----

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: Any) -> datetime:
    """Parse ISO 8601, including `Z` and 7-digit fractions, as aware UTC."""
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return datetime.fromtimestamp(float(text), timezone.utc)
    text = re.sub(r"[zZ]$", "+00:00", text)
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp has no timezone: {value}")
    return parsed.astimezone(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_offset(value: str) -> timedelta:
    parts = [float(part) for part in str(value).strip().split(":")]
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"invalid offset: {value}")
    while len(parts) < 3:
        parts.insert(0, 0.0)
    hours, minutes, seconds = parts
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def display_zone(collection: dict) -> Any:
    name = (collection.get("schedule") or {}).get("timezone")
    if name:
        try:
            return ZoneInfo(str(name))
        except ZoneInfoNotFoundError:
            pass
    return datetime.now().astimezone().tzinfo


def shown(moment: datetime, zone: Any) -> str:
    return moment.astimezone(zone).strftime("%Y-%m-%d %H:%M %Z")


# ---- files ----

def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    return value if isinstance(value, dict) else {}


def write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        yaml.safe_dump(value, handle, sort_keys=False, allow_unicode=True)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def collected_marker(path: Path) -> dict | None:
    """Return the front matter of a workspace-collect inbox file, else None."""
    try:
        with open(path, encoding="utf-8") as handle:
            if handle.readline().strip() != "---":
                return None
            lines = []
            for _ in range(40):
                line = handle.readline()
                if not line or line.strip() == "---":
                    break
                lines.append(line)
    except (OSError, UnicodeDecodeError):
        return None
    try:
        front = yaml.safe_load("".join(lines))
    except yaml.YAMLError:
        return None
    if isinstance(front, dict) and front.get("collected_by") == COLLECTED_BY:
        return front
    return None


def collected_in_inbox() -> list[dict]:
    if not INBOX.is_dir():
        return []
    found = []
    for path in sorted(INBOX.iterdir()):
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() == ".md":
            front = collected_marker(path)
            if front:
                found.append({"path": rel(path), "source_id": front.get("source_id"), "source": front.get("source")})
    return found


# ---- sources ----

def system_for(platform_name: str) -> str | None:
    lowered = platform_name.lower()
    if "slack" in lowered:
        return "slack"
    if "team" in lowered:
        return "microsoft-teams"
    return None


def collect_sources(record: dict) -> list[dict]:
    """Every location marked collect: true, in record order."""
    sources = []
    for platform in record.get("messaging_platforms") or []:
        if not isinstance(platform, dict):
            continue
        system = system_for(str(platform.get("name", "")))
        for location in platform.get("locations") or []:
            if isinstance(location, dict) and location.get("collect") is True:
                sources.append({
                    "location": location,
                    "system": system,
                    "connection_state": platform.get("connection_state"),
                })
    for key in ("sharepoint_locations", "project_sources"):
        for location in record.get(key) or []:
            if isinstance(location, dict) and location.get("collect") is True:
                system = "sharepoint" if key == "sharepoint_locations" else str(location.get("kind", "other"))
                sources.append({"location": location, "system": system, "connection_state": None})
    return sources


def source_entry(source: dict, state: dict, contracts_dir: Path | None) -> dict:
    location = source["location"]
    system = source["system"]
    source_id = str(location.get("id", ""))
    access = location.get("access") if isinstance(location.get("access"), dict) else {}
    contract = contracts_dir / f"{system}.yaml" if contracts_dir and system else None
    entry = {
        "id": source_id,
        "system": system,
        "label": location.get("name") or location.get("label") or source_id,
        "location_type": location.get("location_type", "channel"),
        "locator": location.get("locator"),
        "identifiers": location.get("identifiers") or {},
        "contract": str(contract) if contract else None,
    }
    skipped = None
    if location.get("enabled") is False:
        skipped = "The source is disabled in the project communications record."
    elif source["connection_state"] == "not connected":
        skipped = "The platform was not connected when the source was saved."
    elif access.get("state") == "unavailable":
        skipped = "The source is marked unavailable in the project communications record."
    elif contracts_dir and (contract is None or not contract.exists()):
        skipped = f"No collection contract exists for {system}."
    if skipped:
        entry["skipped"] = skipped
    cursor = ((state.get("sources") or {}).get(source_id) or {}).get("cursor")
    entry["cursor"] = cursor
    if cursor:
        entry["cursor_epoch"] = f"{parse_time(cursor).timestamp():.6f}"
    return entry


def find_source(source_id: str) -> dict:
    for source in collect_sources(load_yaml(SOURCE_CONTEXT_FILE)):
        if str(source["location"].get("id", "")) == source_id:
            return source
    raise SystemExit(f"{source_id} is not marked for collection in {rel(SOURCE_CONTEXT_FILE)}")


def source_state(state: dict, source_id: str) -> dict:
    return state.setdefault("sources", {}).setdefault(source_id, {})


# ---- rendering ----

def entry_time(entry: dict, started_at: datetime | None) -> datetime:
    if entry.get("at"):
        return parse_time(entry["at"])
    if entry.get("offset") is not None and started_at is not None:
        return started_at + parse_offset(entry["offset"])
    raise ValueError(f"entry needs `at`, or `offset` with the document's `started_at`: {entry.get('id')}")


def quoted(text: str) -> str:
    return "\n".join("> " + line if line else ">" for line in str(text).splitlines() or [""])


def render_messages(entries: list[dict], zone: Any) -> list[str]:
    by_id = {str(e["id"]): e for e in entries if e.get("id") is not None}
    replies: dict[str, list[dict]] = {}
    roots = []
    for entry in entries:
        parent = entry.get("parent")
        if parent is not None and str(parent) != str(entry.get("id")):
            replies.setdefault(str(parent), []).append(entry)
        else:
            roots.append(entry)
    lines = []
    for root in roots:
        note = " (earlier message, shown for context)" if root.get("context") else ""
        lines += [f"### {root.get('author') or 'Unknown'} — {shown(root['_at'], zone)}{note}", "", str(root.get("text", "")), ""]
        for reply in replies.pop(str(root.get("id")), []):
            lines += [quoted(f"**Reply from {reply.get('author') or 'Unknown'}, {shown(reply['_at'], zone)}:** {reply.get('text', '')}"), ""]
    for parent_id, orphans in replies.items():
        if parent_id in by_id:
            continue
        lines += [f"### Replies in an earlier thread ({parent_id})", ""]
        for reply in orphans:
            lines += [quoted(f"**Reply from {reply.get('author') or 'Unknown'}, {shown(reply['_at'], zone)}:** {reply.get('text', '')}"), ""]
    return lines


def render_transcript(entries: list[dict], zone: Any) -> list[str]:
    return [f"- [{entry['_at'].astimezone(zone).strftime('%H:%M:%S')}] **{entry.get('author') or 'Unknown'}:** {entry.get('text', '')}" for entry in entries] + [""]


def unique_name(stem: str) -> Path:
    for index in range(1, 1000):
        name = f"{stem}.md" if index == 1 else f"{stem}-{index}.md"
        if not (INBOX / name).exists() and not (INBOX / f".{name}.partial").exists():
            return INBOX / name
    raise SystemExit(f"Could not find a free inbox filename for {stem}")


def safe_locator(locator: Any) -> Any:
    """Drop query strings from Teams links so meeting passcodes are never stored."""
    if isinstance(locator, str) and "teams.microsoft.com" in locator:
        return locator.split("?", 1)[0]
    return locator


def write_document(source: dict, document: dict, entries: list[dict], zone: Any) -> Path:
    location = source["location"]
    times = [entry["_at"] for entry in entries if not entry.get("context")] or [entry["_at"] for entry in entries]
    covered_from, covered_to = min(times), max(times)
    label = location.get("name") or location.get("label") or location.get("id")
    front = {
        "collected_by": COLLECTED_BY,
        "source_id": location.get("id"),
        "source": f"{SYSTEMS.get(source['system'], source['system'])} {label}",
        "system": source["system"],
        "location_type": location.get("location_type", "channel"),
        "locator": safe_locator(location.get("locator")),
        "document_key": document.get("key"),
        "covered_from": iso(covered_from),
        "covered_to": iso(covered_to),
        "collected_at": iso(now_utc()),
    }
    front = {key: value for key, value in front.items() if value is not None}
    title = document.get("title") or f"{front['source']} — new messages"
    zone_name = covered_to.astimezone(zone).strftime("%Z")
    body = ["---", yaml.safe_dump(front, sort_keys=False, allow_unicode=True).rstrip(), "---", "", f"# {title}", "",
            f"Collected automatically by workspace-collect from {front['source']}. Times are {zone_name}.", ""]
    if document.get("format") == "transcript":
        body += render_transcript(entries, zone)
    else:
        body += render_messages(entries, zone)
    # Date and time keep names distinct from files already filed out of the inbox.
    stem = f"{covered_to.astimezone(zone).strftime('%Y-%m-%d-%H%M')}-{location.get('id')}"
    target = unique_name(stem)
    INBOX.mkdir(parents=True, exist_ok=True)
    partial = INBOX / f".{target.name}.partial"
    partial.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
    os.replace(partial, target)
    return target


# ---- commands ----

def command_plan(args: argparse.Namespace) -> dict:
    record = load_yaml(SOURCE_CONTEXT_FILE)
    if not record:
        raise SystemExit(f"No project communications record at {rel(SOURCE_CONTEXT_FILE)}")
    state = load_yaml(COLLECTION_STATE_FILE)
    sources = collect_sources(record)
    if args.since:
        start = iso(parse_time(args.since))
        for source in sources:
            entry = source_state(state, str(source["location"].get("id", "")))
            entry.setdefault("cursor", start)
        write_yaml(COLLECTION_STATE_FILE, state)
    contracts_dir = Path(args.contracts_dir).resolve() if args.contracts_dir else None
    entries = [source_entry(source, state, contracts_dir) for source in sources]
    return {
        "sources": [e for e in entries if "skipped" not in e],
        "skipped": [e for e in entries if "skipped" in e],
        "needs_start": [e["id"] for e in entries if "skipped" not in e and not e["cursor"]],
        "schedule": load_yaml(COLLECTION_FILE).get("schedule"),
    }


def command_write(args: argparse.Namespace) -> dict:
    with open(args.input, encoding="utf-8") as handle:
        payload = json.load(handle)
    source_id = str(payload.get("source_id", ""))
    source = find_source(source_id)
    state = load_yaml(COLLECTION_STATE_FILE)
    current = source_state(state, source_id)
    if not current.get("cursor"):
        raise SystemExit(f"{source_id} has no cursor yet; run `plan --since` or `schedule` first")
    cursor = parse_time(current["cursor"])
    seen = list(current.get("seen") or [])
    zone = display_zone(load_yaml(COLLECTION_FILE))
    # Parse every timestamp before writing anything, so bad input writes no files.
    parsed = []
    for document in payload.get("documents") or []:
        started_at = parse_time(document["started_at"]) if document.get("started_at") else None
        entries = [dict(entry) for entry in document.get("entries") or []]
        for entry in entries:
            entry["_at"] = entry_time(entry, started_at)
        parsed.append((document, entries))
    written: list[str] = []
    candidates: list[datetime] = []
    for document, entries in parsed:
        key = document.get("key")
        if key is not None and str(key) in seen:
            continue
        if document.get("cursor_at"):
            mark = parse_time(document["cursor_at"])
            if mark <= cursor:
                continue
            kept = entries
        else:
            fresh = [entry for entry in entries if not entry.get("context") and entry["_at"] > cursor]
            if not fresh:
                continue
            mark = max(entry["_at"] for entry in fresh)
            parents = {str(entry.get("parent")) for entry in fresh if entry.get("parent") is not None}
            kept = [entry for entry in entries if entry in fresh or (entry.get("context") and str(entry.get("id")) in parents)]
        kept.sort(key=lambda entry: entry["_at"])
        if not kept:
            continue
        written.append(rel(write_document(source, document, kept, zone)))
        candidates.append(mark)
        if key is not None:
            seen.append(str(key))
    if candidates:
        current["cursor"] = iso(max(max(candidates), cursor))
    current["seen"] = seen[-SEEN_LIMIT:]
    current["last_result"] = {
        "at": iso(now_utc()),
        "outcome": "collected" if written else "nothing_new",
        "files": written,
    }
    write_yaml(COLLECTION_STATE_FILE, state)
    return {"source_id": source_id, "files": written, "cursor": current["cursor"]}


def command_fail(args: argparse.Namespace) -> dict:
    find_source(args.source_id)
    state = load_yaml(COLLECTION_STATE_FILE)
    current = source_state(state, args.source_id)
    current["last_result"] = {"at": iso(now_utc()), "outcome": "failed", "reason": args.reason}
    write_yaml(COLLECTION_STATE_FILE, state)
    return {"source_id": args.source_id, "recorded": "failed", "cursor": current.get("cursor")}


def command_schedule(args: argparse.Namespace) -> dict:
    try:
        ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError as exc:
        raise SystemExit(f"Unknown timezone: {args.timezone}") from exc
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", args.time):
        raise SystemExit("--time must be HH:MM in 24-hour time")
    if args.frequency == "weekly" and not args.weekday:
        raise SystemExit("--weekday is required for a weekly schedule")
    collection = load_yaml(COLLECTION_FILE)
    started = iso(now_utc())
    schedule = {
        "frequency": args.frequency,
        "weekday": args.weekday if args.frequency == "weekly" else None,
        "time": args.time,
        "timezone": args.timezone,
        "host": args.host,
        "task_id": args.task_id,
        "created_at": (collection.get("schedule") or {}).get("created_at") or started,
        "updated_at": started,
    }
    collection["schedule"] = {key: value for key, value in schedule.items() if value is not None}
    write_yaml(COLLECTION_FILE, collection)
    state = load_yaml(COLLECTION_STATE_FILE)
    started_ids = []
    for source in collect_sources(load_yaml(SOURCE_CONTEXT_FILE)):
        entry = source_state(state, str(source["location"].get("id", "")))
        if not entry.get("cursor"):
            entry["cursor"] = started
            started_ids.append(source["location"].get("id"))
    write_yaml(COLLECTION_STATE_FILE, state)
    return {"schedule": collection["schedule"], "cursors_started": started_ids}


def command_unschedule(args: argparse.Namespace) -> dict:
    collection = load_yaml(COLLECTION_FILE)
    removed = collection.pop("schedule", None)
    write_yaml(COLLECTION_FILE, collection)
    return {"removed": removed}


def command_status(args: argparse.Namespace) -> dict:
    state = load_yaml(COLLECTION_STATE_FILE)
    return {
        "schedule": load_yaml(COLLECTION_FILE).get("schedule"),
        "sources": {
            source_id: {"cursor": entry.get("cursor"), "last_result": entry.get("last_result")}
            for source_id, entry in (state.get("sources") or {}).items()
        },
        "collected_in_inbox": collected_in_inbox(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--contracts-dir", help="workspace-collect's contracts/ folder")
    plan.add_argument("--since", help="ISO time to start any source that has no cursor yet")
    plan.set_defaults(func=command_plan)
    write = commands.add_parser("write")
    write.add_argument("--input", required=True, help="JSON file of collected documents for one source")
    write.set_defaults(func=command_write)
    fail = commands.add_parser("fail")
    fail.add_argument("--source-id", required=True)
    fail.add_argument("--reason", required=True)
    fail.set_defaults(func=command_fail)
    schedule = commands.add_parser("schedule")
    schedule.add_argument("--frequency", choices=("weekly", "daily"), required=True)
    schedule.add_argument("--weekday", choices=("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"))
    schedule.add_argument("--time", required=True, help="HH:MM, 24-hour")
    schedule.add_argument("--timezone", required=True, help="IANA name, for example America/New_York")
    schedule.add_argument("--host", required=True, help="Agent host that runs the task, for example codex")
    schedule.add_argument("--task-id", required=True, help="The host's ID for the scheduled task")
    schedule.set_defaults(func=command_schedule)
    commands.add_parser("unschedule").set_defaults(func=command_unschedule)
    commands.add_parser("status").set_defaults(func=command_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = args.func(args)
    except (ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

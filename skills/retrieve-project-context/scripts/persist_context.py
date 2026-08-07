#!/usr/bin/env python3
"""Persist a bounded project-context pack as a summary-to-evidence hierarchy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a JSON object in {path}")
    return value


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def safe_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    if not normalized or normalized != value:
        raise SystemExit(f"Unsafe source_id: {value}")
    return normalized


def require_string(value: dict[str, Any], field: str, context: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result.strip():
        raise SystemExit(f"{context}.{field} must be a non-empty string")
    return result.strip()


def trim_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def md(value: Any) -> str:
    return str(value).replace("|", "\\|")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "sources": {}, "runs": [], "gaps": []}
    state = read_json(path)
    if not isinstance(state.get("sources", {}), dict):
        state["sources"] = {}
    if not isinstance(state.get("runs", []), list):
        state["runs"] = []
    if not isinstance(state.get("gaps", []), list):
        state["gaps"] = []
    return state


def load_gaps(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read access gaps {path}: {exc}") from exc
    if not isinstance(value, list):
        raise SystemExit(f"Access gaps must be a JSON array: {path}")
    return value


def validate_gap(gap: Any, index: int, manifest_sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(gap, dict):
        raise SystemExit(f"access_gaps[{index}] must be an object")
    source_id = safe_id(require_string(gap, "source_id", f"access_gaps[{index}]"))
    if source_id not in manifest_sources:
        raise SystemExit(f"Unknown source_id in access gap: {source_id}")
    state = gap.get("state")
    if state not in {"unavailable", "unknown"}:
        raise SystemExit(f"access_gaps[{index}].state must be unavailable or unknown")
    reason = require_string(gap, "reason", f"access_gaps[{index}]")
    if len(reason) > 240 or "\n" in reason:
        raise SystemExit(f"access_gaps[{index}].reason must be a short single-line string of at most 240 characters")
    normalized = dict(gap)
    normalized.update({
        "source_id": source_id,
        "label": gap.get("label") or manifest_sources[source_id].get("label", source_id),
        "locator": gap.get("locator") or manifest_sources[source_id].get("locator", ""),
        "state": state,
        "reason": reason,
    })
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--context-dir", type=Path, required=True)
    parser.add_argument("--gaps", type=Path, help="Optional JSON array of access gaps emitted by ranking")
    args = parser.parse_args()

    manifest = read_json(args.manifest)
    pack = read_json(args.pack)
    task = require_string(pack, "task", "pack")
    overview = require_string(pack, "overview", "pack")
    decisions = pack.get("decisions", [])
    questions = pack.get("open_questions", [])
    packed_sources = pack.get("sources")
    if not isinstance(decisions, list) or not all(isinstance(item, str) for item in decisions):
        raise SystemExit("pack.decisions must be an array of strings")
    if not isinstance(questions, list) or not all(isinstance(item, str) for item in questions):
        raise SystemExit("pack.open_questions must be an array of strings")
    if not isinstance(packed_sources, list) or not packed_sources:
        raise SystemExit("pack.sources must be a non-empty array")

    manifest_sources = {
        source["id"]: source
        for source in manifest.get("sources", [])
        if isinstance(source, dict) and source.get("id")
    }
    raw_gaps = pack.get("access_gaps", [])
    if not isinstance(raw_gaps, list):
        raise SystemExit("pack.access_gaps must be an array")
    if args.gaps:
        raw_gaps = [*raw_gaps, *load_gaps(args.gaps)]
    gaps_by_source: dict[str, dict[str, Any]] = {}
    for index, gap in enumerate(raw_gaps):
        normalized_gap = validate_gap(gap, index, manifest_sources)
        gaps_by_source[normalized_gap["source_id"]] = normalized_gap
    access_gaps = list(gaps_by_source.values())
    policy = manifest.get("source_policy", {})
    max_excerpt = int(policy.get("max_excerpt_chars", 1200))
    max_total = int(policy.get("max_total_chars", 12000))
    if max_excerpt < 1 or max_total < 1:
        raise SystemExit("Excerpt limits must be positive")

    timestamp = now_iso()
    index_sections: list[tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]] = []
    total_chars = 0
    seen_chunk_ids: set[str] = set()
    for position, packed_source in enumerate(packed_sources):
        if not isinstance(packed_source, dict):
            raise SystemExit(f"pack.sources[{position}] must be an object")
        source_id = safe_id(require_string(packed_source, "source_id", f"pack.sources[{position}]"))
        if source_id not in manifest_sources:
            raise SystemExit(f"Unknown source_id in pack: {source_id}")
        access = manifest_sources[source_id].get("access")
        if isinstance(access, dict) and access.get("state") in {"unavailable", "unknown"}:
            raise SystemExit(f"Cannot persist excerpts from inaccessible source: {source_id}")
        summary = require_string(packed_source, "summary", f"pack.sources[{position}]")
        excerpts = packed_source.get("excerpts")
        if not isinstance(excerpts, list) or not excerpts:
            raise SystemExit(f"pack source {source_id} must contain excerpts")
        normalized: list[dict[str, Any]] = []
        for excerpt_position, excerpt in enumerate(excerpts):
            if not isinstance(excerpt, dict):
                raise SystemExit(f"Excerpt {excerpt_position} for {source_id} must be an object")
            chunk_id = require_string(excerpt, "chunk_id", f"excerpt {excerpt_position}")
            if chunk_id in seen_chunk_ids:
                raise SystemExit(f"Duplicate chunk_id in pack: {chunk_id}")
            seen_chunk_ids.add(chunk_id)
            if excerpt.get("source_id") != source_id:
                raise SystemExit(f"Chunk {chunk_id} does not match source {source_id}")
            text = require_string(excerpt, "text", f"chunk {chunk_id}")
            remaining = max_total - total_chars
            if remaining <= 0:
                break
            bounded = trim_text(text, min(max_excerpt, remaining))
            clean = dict(excerpt)
            clean["text"] = bounded
            normalized.append(clean)
            total_chars += len(bounded)
        if not normalized:
            break
        packed_source = dict(packed_source)
        packed_source["summary"] = summary
        index_sections.append((manifest_sources[source_id], packed_source, normalized))

    if not index_sections:
        raise SystemExit("No excerpts remained within the manifest character budget")

    sources_root = args.context_dir / "sources"
    for source, packed_source, excerpts in index_sections:
        source_id = source["id"]
        source_dir = sources_root / source_id
        excerpt_lines = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in excerpts)
        atomic_write(source_dir / "excerpts.jsonl", excerpt_lines)

        summary_lines = [
            f"# {source.get('label', source_id)}",
            "",
            packed_source["summary"],
            "",
            f"- Source ID: `{source_id}`",
            f"- Kind: {source.get('kind', 'unknown')}",
            f"- Locator: `{source.get('locator', '')}`",
            f"- Retrieved: {timestamp}",
            "",
            "## Selected Evidence",
            "",
        ]
        for excerpt in excerpts:
            title = excerpt.get("title") or excerpt["chunk_id"]
            score = excerpt.get("_ranking", {}).get("score", "unscored")
            summary_lines.extend([f"### {title}", "", excerpt["text"], ""])
            metadata = [f"score: {score}"]
            for field in ("author", "timestamp", "url"):
                if excerpt.get(field):
                    metadata.append(f"{field}: {excerpt[field]}")
            summary_lines.extend(["; ".join(metadata), ""])
        atomic_write(source_dir / "summary.md", "\n".join(summary_lines))

    index_lines = [
        "# Ranked Project Context",
        "",
        f"- Task: {task}",
        f"- Refreshed: {timestamp}",
        f"- Evidence characters: {total_chars}",
        "",
        "## Briefing",
        "",
        overview,
        "",
        "## Decisions",
        "",
    ]
    index_lines.extend(f"- {item}" for item in decisions)
    if not decisions:
        index_lines.append("- None identified")
    index_lines.extend(["", "## Open Questions", ""])
    index_lines.extend(f"- {item}" for item in questions)
    if not questions:
        index_lines.append("- None identified")
    index_lines.extend(["", "## Access Gaps", ""])
    if access_gaps:
        for gap in access_gaps:
            index_lines.append(
                f"- `{gap['source_id']}` {gap.get('label', gap['source_id'])} ({gap['state']}): {gap['reason']} "
                f"(`{gap.get('locator', '')}`)"
            )
    else:
        index_lines.append("- None recorded")
    index_lines.extend(["", "## Sources", "", "| Priority | Source | Summary |", "| ---: | --- | --- |"])
    for source, packed_source, excerpts in index_sections:
        link = f"sources/{source['id']}/summary.md"
        index_lines.append(
            f"| {source.get('priority', '')} | [{md(source.get('label', source['id']))}]({link}) "
            f"({len(excerpts)} excerpts) | {md(packed_source['summary'])} |"
        )
    index_lines.append("")
    atomic_write(args.context_dir / "index.md", "\n".join(index_lines))

    state_path = args.context_dir / "state.json"
    state = load_state(state_path)
    manifest_hash = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    for source, _, excerpts in index_sections:
        state["sources"][source["id"]] = {
            "last_retrieved_at": timestamp,
            "chunk_count": len(excerpts),
            "locator": source.get("locator"),
        }
    state["manifest_sha256"] = manifest_hash
    state["last_refresh_at"] = timestamp
    state["last_task"] = task
    state["gaps"].extend(access_gaps)
    state["gaps"] = state["gaps"][-20:]
    state["runs"].append({"task": task, "refreshed_at": timestamp, "source_ids": [item[0]["id"] for item in index_sections]})
    state["runs"] = state["runs"][-20:]
    atomic_write(state_path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    print(f"Persisted {len(index_sections)} sources, {total_chars} evidence characters, and {len(access_gaps)} access gaps -> {args.context_dir / 'index.md'}")


if __name__ == "__main__":
    main()

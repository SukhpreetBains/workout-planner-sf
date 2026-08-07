#!/usr/bin/env python3
"""Rank normalized project-context chunks with a deterministic RAG-style heuristic."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is",
    "it", "of", "on", "or", "that", "the", "this", "to", "was", "what", "when", "where",
    "which", "who", "with",
}
AUTHORITY = {"canonical": 1.0, "supporting": 0.65, "historical": 0.35}
LOW_SIGNAL = re.compile(r"^\s*(thanks|thank you|ok|okay|got it|sounds good|ack|\+1|👍|✅)[.!\s]*$", re.I)


def tokenize(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_-]+", value.lower())
        if token not in STOPWORDS and len(token) > 1
    }


def overlap(needles: set[str], haystack: set[str]) -> float:
    if not needles:
        return 0.0
    return len(needles & haystack) / len(needles)


def parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value)
    try:
        if re.fullmatch(r"\d+(\.\d+)?", text):
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OSError, OverflowError):
        return None


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a JSON object in {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SystemExit(f"Unable to read {path}: {exc}") from exc
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON on {path}:{number}: {exc}") from exc
        if not isinstance(item, dict):
            raise SystemExit(f"Expected an object on {path}:{number}")
        for field in ("chunk_id", "source_id", "text"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise SystemExit(f"Missing non-empty {field} on {path}:{number}")
        if item["chunk_id"] in seen_ids:
            raise SystemExit(f"Duplicate chunk_id {item['chunk_id']} on {path}:{number}")
        seen_ids.add(item["chunk_id"])
        semantic = item.get("semantic_score")
        if semantic is not None and (not isinstance(semantic, (int, float)) or not 0 <= semantic <= 1):
            raise SystemExit(f"semantic_score must be from 0 to 1 on {path}:{number}")
        items.append(item)
    return items


def recency_score(timestamp: datetime | None, freshness_hours: int, now: datetime) -> float:
    if freshness_hours == 0:
        return 1.0
    if timestamp is None:
        return 0.35
    age_hours = max(0.0, (now - timestamp).total_seconds() / 3600)
    return math.exp(-math.log(2) * age_hours / max(freshness_hours, 1))


def rank_item(
    item: dict[str, Any],
    source: dict[str, Any],
    task_tokens: set[str],
    project_tokens: set[str],
    now: datetime,
) -> dict[str, Any]:
    text = item["text"]
    title_tokens = tokenize(str(item.get("title", "")))
    body_tokens = tokenize(text)
    lexical = min(1.0, 0.65 * overlap(task_tokens, body_tokens) + 0.35 * overlap(task_tokens, title_tokens))
    project_overlap = overlap(project_tokens, body_tokens | title_tokens) if project_tokens else 0.0
    lexical = min(1.0, lexical + 0.15 * project_overlap)
    supplied = item.get("semantic_score")
    relevance = lexical if supplied is None else 0.7 * float(supplied) + 0.3 * lexical

    source_text = " ".join([str(source.get("purpose", "")), *source.get("query_hints", [])])
    source_fit = overlap(task_tokens, tokenize(source_text))
    authority = AUTHORITY.get(source.get("authority"), 0.5)
    priority = max(1, min(5, int(source.get("priority", 3)))) / 5
    freshness = int(source.get("freshness_hours", 168))
    recency = recency_score(parse_timestamp(item.get("timestamp")), freshness, now)
    penalty = 12.0 if LOW_SIGNAL.fullmatch(text) else 0.0
    if item.get("is_bot") is True:
        penalty += 5.0

    score = max(0.0, min(100.0, 60 * relevance + 10 * source_fit + 10 * authority + 10 * priority + 10 * recency - penalty))
    ranked = dict(item)
    ranked["_ranking"] = {
        "score": round(score, 2),
        "task_relevance": round(relevance, 4),
        "source_fit": round(source_fit, 4),
        "authority": round(authority, 4),
        "priority": round(priority, 4),
        "recency": round(recency, 4),
        "penalty": round(penalty, 2),
        "method": "semantic-plus-lexical" if supplied is not None else "lexical-fallback",
    }
    return ranked


def jaccard(left: str, right: str) -> float:
    a, b = tokenize(left), tokenize(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top-n", type=int, default=24)
    parser.add_argument("--max-per-source", type=int, default=6)
    parser.add_argument("--min-score", type=float, default=15.0)
    args = parser.parse_args()

    if args.top_n < 1 or args.max_per_source < 1:
        raise SystemExit("--top-n and --max-per-source must be positive")
    manifest = read_json(args.manifest)
    sources = {
        source["id"]: source
        for source in manifest.get("sources", [])
        if isinstance(source, dict) and source.get("enabled", True) and source.get("id")
    }
    chunks = read_jsonl(args.chunks)
    unknown = sorted({chunk["source_id"] for chunk in chunks} - set(sources))
    if unknown:
        raise SystemExit(f"Chunks reference missing or disabled sources: {', '.join(unknown)}")

    project = manifest.get("project", {})
    project_text = " ".join([
        str(project.get("objective", "")),
        str(project.get("current_phase", "")),
        *project.get("terms", []),
    ])
    task_tokens = tokenize(args.task)
    project_tokens = tokenize(project_text)
    now = datetime.now(timezone.utc)
    ranked = [rank_item(chunk, sources[chunk["source_id"]], task_tokens, project_tokens, now) for chunk in chunks]
    ranked.sort(key=lambda item: (-item["_ranking"]["score"], item["chunk_id"]))

    policy = manifest.get("source_policy", {})
    max_excerpt_chars = int(policy.get("max_excerpt_chars", 1200))
    max_total_chars = int(policy.get("max_total_chars", 12000))
    if max_excerpt_chars < 1 or max_total_chars < 1:
        raise SystemExit("Manifest excerpt limits must be positive")
    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    total_chars = 0
    for item in ranked:
        if item["_ranking"]["score"] < args.min_score:
            continue
        source_id = item["source_id"]
        if counts.get(source_id, 0) >= args.max_per_source:
            continue
        if any(jaccard(item["text"], previous["text"]) >= 0.85 for previous in selected):
            continue
        if len(item["text"]) > max_excerpt_chars:
            item = dict(item)
            item["text"] = item["text"][: max_excerpt_chars - 1].rstrip() + "…"
        size = len(item["text"])
        if selected and total_chars + size > max_total_chars:
            continue
        selected.append(item)
        counts[source_id] = counts.get(source_id, 0) + 1
        total_chars += size
        if len(selected) >= args.top_n:
            break

    content = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in selected)
    atomic_write(args.output, content)
    print(f"Ranked {len(chunks)} chunks; selected {len(selected)} ({total_chars} characters) -> {args.output}")


if __name__ == "__main__":
    main()

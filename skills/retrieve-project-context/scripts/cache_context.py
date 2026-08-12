#!/usr/bin/env python3
"""Report whether a recorded source cache is eligible for deterministic reuse."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STOPWORDS = {"a", "an", "and", "as", "at", "be", "by", "for", "from", "in", "is", "of", "on", "or", "the", "to", "with"}


def tokens(value: str) -> set[str]:
    return {item for item in re.findall(r"[a-z0-9][a-z0-9_-]+", value.lower()) if item not in STOPWORDS and len(item) > 1}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--context-dir", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--now", help="UTC ISO timestamp for deterministic validation")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    state_path = args.context_dir / "state.json"
    index_path = args.context_dir / "index.md"
    sources = {source.get("id"): source for source in manifest.get("sources", []) if isinstance(source, dict)}
    source = sources.get(args.source_id)
    result: dict[str, Any] = {"source_id": args.source_id, "reuse": False}
    if not source:
        result["reason"] = "Source is not recorded in the manifest."
    elif not index_path.exists() or not state_path.exists():
        result["reason"] = "Cached hierarchy is absent."
    else:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        cached = state.get("sources", {}).get(args.source_id)
        access = source.get("access") or {"state": "available"}
        source_tokens = tokens(" ".join([str(source.get("purpose", "")), *source.get("query_hints", [])]))
        task_tokens = tokens(args.task)
        freshness_hours = int(source.get("freshness_hours", manifest.get("source_policy", {}).get("default_freshness_hours", 168)))
        now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        try:
            retrieved = parse_time(str(cached["last_retrieved_at"])) if cached else None
        except (KeyError, TypeError, ValueError):
            retrieved = None
        age_hours = None if retrieved is None else max(0.0, (now - retrieved).total_seconds() / 3600)
        result.update({"age_hours": age_hours, "freshness_hours": freshness_hours, "cached_at": cached.get("last_retrieved_at") if cached else None})
        if access.get("state") != "available":
            result["reason"] = "Source access is not available; preserve it as a retrieval gap."
        elif cached and cached.get("locator") != source.get("locator"):
            result["reason"] = "The recorded source locator changed after this cache was created."
        elif not (source_tokens & task_tokens):
            result["reason"] = "Cached source purpose does not overlap the task."
        elif retrieved is None:
            result["reason"] = "Cached source has no retrieval timestamp."
        elif freshness_hours == 0 or (age_hours is not None and age_hours <= freshness_hours):
            result["reuse"] = True
            result["reason"] = "Cached source is within its recorded freshness window."
        else:
            result["reason"] = "Cached source is stale for this task."
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

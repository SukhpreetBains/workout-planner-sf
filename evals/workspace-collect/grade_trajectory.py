#!/usr/bin/env python3
"""Grade scheduled workspace-collect runs from Codex session logs.

A Codex session log (`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`) records
every tool call. This grader reads only the turns Codex started on a
schedule (`turn_trigger: automation_cron_scheduled`) whose prompt invokes
`$workspace-collect`. A later turn where the user replies "ingest" is
expected to run workspace-add, so it is never graded here.

A scheduled turn fails when it:

- runs any workspace-add step (batch selection, document reading, proposal
  validation or writes, the review server, tracker writes, a full sync);
- moves, renames, or deletes a file in workspace/inbox/;
- uses a browser, desktop, or screen tool;
- searches Slack or Teams, or calls a Slack or Teams tool that no contract
  in workspace-collect/contracts/ lists;
- changes the schedule from inside a scheduled run.

Each graded turn also reports its total tokens from the log's token counts.

Usage:
    python3 evals/workspace-collect/grade_trajectory.py <rollout.jsonl> [...]
    python3 evals/workspace-collect/grade_trajectory.py --scan ~/.codex/sessions --since 2026-10-20
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "plugins" / "ascent" / "skills" / "workspace-collect" / "contracts"

# Connector namespaces the contracts govern. Any call in these namespaces
# must be an operation a contract lists.
GOVERNED_PREFIXES = ("slack.", "microsoft_teams.")
FORBIDDEN_TOOL = re.compile(r"(^|[._])(cua|browser|computer|screen|playwright|chrome)", re.IGNORECASE)
SCHEDULE_TOOLS = {"automation_update"}
# A script counts only when an interpreter or the Ascent launcher runs it,
# not when a search or a read merely names it.
RUNS_SCRIPT = r"(?:/py|python[0-9.]*)['\"]?\s+(?:-\S+\s+)*['\"]?\S*"
WORKSPACE_ADD_SCRIPT = re.compile(RUNS_SCRIPT + r"(?:select_inbox_batch|read_document|validate_updates|apply_updates|review_server)\.py")
FULL_SYNC = re.compile(RUNS_SCRIPT + r"sync\.py(?!['\"]?\s+--check-setup)")
GOVERNED_WRITE = re.compile(r"(?:>|\btee\b|\bmv\b|\bcp\b)[^|;&]*workspace/(?:\.system/proposed-updates|trackers)/")
TOKEN_KEYS = ("total_tokens", "input_tokens", "cached_input_tokens", "output_tokens")
INBOX_MUTATION = re.compile(r"\b(mv|rm|cp\s+-f|unlink)\b[^|;&]*workspace/inbox/")


def contract_operations(contracts_dir: Path = CONTRACTS) -> set[str]:
    """Tool names listed under `operations:` in every contract (no YAML dependency)."""
    tools: set[str] = set()
    for path in sorted(contracts_dir.glob("*.yaml")):
        tools.update(re.findall(r"^\s+tool:\s*([A-Za-z0-9_]+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE))
    return tools


def turns(lines: list[str]) -> list[dict]:
    """Split a rollout log into turns with their trigger, prompt, and events."""
    found: list[dict] = []
    current: dict | None = None
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        kind = payload.get("type")
        if kind == "task_started":
            current = {
                "trigger": (payload.get("turn_attribution") or {}).get("turn_trigger"),
                "prompt": "",
                "events": [],
                "tokens": None,
                "complete": False,
            }
            found.append(current)
            continue
        if current is None:
            continue
        if kind == "message" and payload.get("role") == "user":
            text = " ".join(part.get("text", "") for part in payload.get("content") or [] if isinstance(part, dict))
            current["prompt"] += text
        elif kind == "token_count":
            info = payload.get("info") or {}
            total, last = info.get("total_token_usage") or {}, info.get("last_token_usage") or {}
            if isinstance(total.get("total_tokens"), int):
                current["tokens_end"] = {key: int(total.get(key) or 0) for key in TOKEN_KEYS}
                current.setdefault("tokens_start", {key: int(total.get(key) or 0) - int(last.get(key) or 0) for key in TOKEN_KEYS})
        elif kind == "item_completed":
            current["events"].append(payload.get("item") or {})
        elif kind == "task_complete":
            current["complete"] = True
    for turn in found:
        if "tokens_end" in turn:
            turn["tokens"] = {key: turn["tokens_end"][key] - turn["tokens_start"][key] for key in TOKEN_KEYS}
    return found


def grade_turn(turn: dict, allowed: set[str]) -> dict:
    violations: list[str] = []
    calls: list[str] = []
    for item in turn["events"]:
        if item.get("type") == "McpToolCall":
            tool = str(item.get("tool") or "")
            server = str(item.get("server") or "")
            calls.append(tool)
            short = tool.split(".", 1)[-1]
            if FORBIDDEN_TOOL.search(server) or FORBIDDEN_TOOL.search(tool):
                violations.append(f"browser-or-desktop-tool: {server}:{tool}")
            elif short in SCHEDULE_TOOLS:
                violations.append(f"schedule-changed-in-scheduled-run: {tool}")
            elif tool.startswith(GOVERNED_PREFIXES):
                if "search" in short:
                    violations.append(f"connector-search: {tool}")
                elif short not in allowed:
                    violations.append(f"tool-not-in-contract: {tool}")
        elif item.get("type") == "CommandExecution":
            command = " ".join(str(part) for part in item.get("command") or [])
            if WORKSPACE_ADD_SCRIPT.search(command) or FULL_SYNC.search(command) or GOVERNED_WRITE.search(command):
                violations.append(f"workspace-add-step: {command[:160]}")
            if INBOX_MUTATION.search(command):
                violations.append(f"inbox-file-changed: {command[:160]}")
    return {
        "outcome": "fail" if violations else "pass",
        "violations": violations,
        "connector_calls": calls,
        "tokens": turn["tokens"],
        "complete": turn["complete"],
    }


def grade_file(path: Path, allowed: set[str]) -> list[dict]:
    results = []
    for index, turn in enumerate(turns(path.read_text(encoding="utf-8").splitlines())):
        if turn["trigger"] != "automation_cron_scheduled" or "$workspace-collect" not in turn["prompt"]:
            continue
        result = grade_turn(turn, allowed)
        result.update({"log": str(path), "turn_index": index})
        results.append(result)
    return results


def scan(root: Path, since: date) -> list[Path]:
    paths = []
    for path in sorted(root.expanduser().glob("*/*/*/rollout-*.jsonl")):
        try:
            day = date(int(path.parts[-4]), int(path.parts[-3]), int(path.parts[-2]))
        except ValueError:
            continue
        if day >= since:
            paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("logs", nargs="*", type=Path)
    parser.add_argument("--scan", type=Path, help="Codex sessions folder to search, for example ~/.codex/sessions")
    parser.add_argument("--since", type=date.fromisoformat, default=date.min, help="With --scan: first day to include")
    args = parser.parse_args()
    paths = list(args.logs) + (scan(args.scan, args.since) if args.scan else [])
    if not paths:
        parser.error("pass rollout logs or --scan")
    allowed = contract_operations()
    results = [result for path in paths for result in grade_file(path, allowed)]
    tokens = [r["tokens"] for r in results if r["tokens"]]
    summary = {
        "suite": "workspace-collect-trajectory",
        "graded_runs": len(results),
        "failed_runs": sum(1 for r in results if r["outcome"] == "fail"),
        "outcome": "pass" if results and all(r["outcome"] == "pass" for r in results) else ("fail" if results else "no-runs"),
        "tokens_per_run": tokens,
        "runs": results,
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["outcome"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

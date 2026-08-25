#!/usr/bin/env python3
"""Run the synthetic, outcome-graded regression suite for project-context skills."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[1]
CASE_PATH = EVAL_DIR / "cases" / "ascent-mobilize-risk-gate-1.json"
DISCOVERY = ROOT / "skills" / "discover-project-context" / "scripts" / "project_context.py"
RANK = ROOT / "skills" / "retrieve-project-context" / "scripts" / "rank_context.py"
PERSIST = ROOT / "skills" / "retrieve-project-context" / "scripts" / "persist_context.py"
CACHE = ROOT / "skills" / "retrieve-project-context" / "scripts" / "cache_context.py"


def run(*args: str, cwd: Path) -> str:
    result = subprocess.run([sys.executable, *args], cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr.strip()}")
    return result.stdout


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    started = time.monotonic()
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="ascent-context-eval-") as temp:
        workspace = Path(temp)
        context_dir = workspace / ".codex" / "project-context"
        project = case["project"]
        run(str(DISCOVERY), "init", "--root", str(workspace), "--name", project["name"], "--objective", project["objective"], cwd=ROOT)
        run(str(DISCOVERY), "set-project", "--root", str(workspace), "--phase", project["phase"], cwd=ROOT)
        for source in case["sources"]:
            args = [str(DISCOVERY), "upsert-source", "--root", str(workspace), "--id", source["id"], "--kind", source["kind"], "--label", source["label"], "--locator", source["locator"], "--purpose", source["purpose"], "--authority", source["authority"], "--priority", str(source["priority"]), "--freshness-hours", str(source["freshness_hours"]), "--access-state", source["access_state"]]
            for hint in source["query_hints"]:
                args.extend(["--query-hint", hint])
            if source.get("access_reason"):
                args.extend(["--access-reason", source["access_reason"]])
            run(*args, cwd=ROOT)
        metrics = case["metrics"]
        args = [str(DISCOVERY), "record-discovery", "--root", str(workspace), "--sources-considered", str(metrics["sources_considered"]), "--sources-recorded", str(metrics["sources_recorded"]), "--connector-calls", str(metrics["connector_calls"]), "--items-inspected", str(metrics["items_inspected"]), "--characters-inspected", str(metrics["characters_inspected"])]
        for cap in metrics["caps"]:
            args.extend(["--cap", cap])
        run(*args, cwd=ROOT)
        run(str(DISCOVERY), "render-brief", "--root", str(workspace), cwd=ROOT)
        run(str(DISCOVERY), "validate", "--root", str(workspace), cwd=ROOT)

        manifest_text = (context_dir / "manifest.json").read_text(encoding="utf-8")
        brief_text = (context_dir / "brief.md").read_text(encoding="utf-8")
        check(case["sentinel"] not in manifest_text + brief_text, "discovery leaked an unavailable source body")
        manifest = json.loads(manifest_text)
        email = next(source for source in manifest["sources"] if source["id"] == "email-threads")
        check(email["access"]["state"] == "unavailable", "unavailable source state was lost")

        retrieval = case["retrieval"]
        chunks_path, ranked_path, gaps_path = workspace / "chunks.jsonl", workspace / "ranked.jsonl", workspace / "gaps.json"
        chunks_path.write_text("".join(json.dumps(chunk) + "\n" for chunk in retrieval["chunks"]), encoding="utf-8")
        run(str(RANK), "--manifest", str(context_dir / "manifest.json"), "--chunks", str(chunks_path), "--task", retrieval["task"], "--output", str(ranked_path), "--top-n", "10", "--max-per-source", str(retrieval["max_per_source"]), "--gaps-output", str(gaps_path), cwd=ROOT)
        ranked = [json.loads(line) for line in ranked_path.read_text(encoding="utf-8").splitlines() if line]
        ranked_ids = {item["chunk_id"] for item in ranked}
        check(set(retrieval["required_chunk_ids"]).issubset(ranked_ids), "required evidence was not selected")
        check(case["sentinel"] not in ranked_path.read_text(encoding="utf-8"), "restricted body reached ranked evidence")
        check(sum(len(item["text"]) for item in ranked) <= retrieval["max_total_chars"], "character budget exceeded")
        gaps = json.loads(gaps_path.read_text(encoding="utf-8"))
        check(any(gap["source_id"] == "email-threads" for gap in gaps), "access gap was not emitted")

        pack = {"task": retrieval["task"], "overview": "Bounded Mobilize evidence.", "access_gaps": gaps, "sources": [{"source_id": item["source_id"], "summary": item["title"], "excerpts": [item]} for item in ranked]}
        pack_path = workspace / "pack.json"
        pack_path.write_text(json.dumps(pack), encoding="utf-8")
        run(str(PERSIST), "--manifest", str(context_dir / "manifest.json"), "--pack", str(pack_path), "--context-dir", str(context_dir), cwd=ROOT)
        check("## Access Gaps" in (context_dir / "index.md").read_text(encoding="utf-8"), "persisted access gap missing")

        stale = json.loads(run(str(CACHE), "--manifest", str(context_dir / "manifest.json"), "--context-dir", str(context_dir), "--source-id", "client-docs", "--task", "validated scope governance", "--now", "2099-01-01T00:00:00Z", cwd=ROOT))
        fresh = json.loads(run(str(CACHE), "--manifest", str(context_dir / "manifest.json"), "--context-dir", str(context_dir), "--source-id", "client-docs", "--task", "validated scope governance", "--now", stale["cached_at"], cwd=ROOT))
        unrelated = json.loads(run(str(CACHE), "--manifest", str(context_dir / "manifest.json"), "--context-dir", str(context_dir), "--source-id", "client-docs", "--task", "unrelated payroll policy", "--now", stale["cached_at"], cwd=ROOT))
        check(not stale["reuse"] and fresh["reuse"] and not unrelated["reuse"], "cache relevance or freshness boundary failed")

    duration = round((time.monotonic() - started) * 1000)
    print(json.dumps({"suite": "context-skills", "outcome": "pass", "evaluated_task_count": 4, "outcome_pass_rate": 1.0, "duration_ms": duration}))


if __name__ == "__main__":
    main()

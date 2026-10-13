#!/usr/bin/env python3
"""Verify the ascent-initial-setup evaluation package and deterministic runner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "ascent-initial-setup"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    profile = json.loads((SUITE / "skill-profile.json").read_text(encoding="utf-8"))
    plan = json.loads((SUITE / "eval-plan.json").read_text(encoding="utf-8"))
    cases = json.loads((SUITE / "cases" / "storage-decisions.json").read_text(encoding="utf-8"))["cases"]
    tasks = [json.loads(line) for line in (SUITE / "cases" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if line]

    check(profile["skill_id"] == "ascent-initial-setup", "profile identifies the wrong skill")
    check(plan["coverage"]["mode"] == "regression", "suite should protect established setup behavior")
    check(plan["runs_per_arm"] >= 3, "reproducibility requires at least three repeats")
    check({task["case_type"] for task in tasks} == {"positive", "negative"}, "suite needs positive and negative tasks")
    check({case["id"] for case in cases} == {"local-only", "existing-sharepoint-account", "missing-sharepoint-account"}, "storage decision fixture is incomplete")

    completed = subprocess.run(
        [sys.executable, str(SUITE / "run_deterministic.py"), "--runs", "1", "--quiet"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    check(completed.returncode == 0, f"runner failed:\n{completed.stdout}\n{completed.stderr}")
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    check(payload["outcome"] == "pass", "runner did not report a passing outcome")
    check(payload["checks_total"] == payload["checks_passed"], "not all declared checks passed")
    check(payload["evaluated_task_count"] == len(tasks), "runner does not represent every task")
    print("Passed ascent-initial-setup evaluation acceptance fixtures")


if __name__ == "__main__":
    main()

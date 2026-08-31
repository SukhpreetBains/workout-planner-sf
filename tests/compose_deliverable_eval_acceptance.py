#!/usr/bin/env python3
"""Verify the compose-deliverable evaluation package and deterministic runner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "compose-deliverable"
RUNNER = SUITE / "run_deterministic.py"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    profile = json.loads((SUITE / "skill-profile.json").read_text(encoding="utf-8"))
    plan = json.loads((SUITE / "eval-plan.json").read_text(encoding="utf-8"))
    tasks = [json.loads(line) for line in (SUITE / "cases" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if line]
    contract = json.loads((SUITE / "cases" / "reference-informed-source.json").read_text(encoding="utf-8"))
    check(profile["skill_id"] == "compose-deliverable", "profile identifies the wrong skill")
    check(profile["deliverable"]["kind"] == "document", "PPTX is a document deliverable")
    check(plan["coverage"]["mode"] == "hybrid", "suite should protect regression behavior and capability")
    check(plan["arms"]["baseline-no-skills"]["status"] == "not-implemented", "baseline gap must remain explicit")
    check({task["case_type"] for task in tasks} == {"positive", "negative"}, "suite needs positive and negative task contracts")
    check(contract["required_native_text"], "source contract must declare independently checked text")
    result = subprocess.run([sys.executable, str(RUNNER), "--quiet"], cwd=ROOT, text=True, capture_output=True, check=False)
    check(result.returncode == 0, f"runner failed: {result.stderr}")
    payload = json.loads(result.stdout)
    check(payload["outcome"] == "pass", "runner did not report a passing outcome")
    check(payload["checks_total"] == 7 and payload["checks_passed_min"] == 7, "runner did not report all seven checks")
    check(payload["evaluated_task_count"] == 2, "runner does not represent both task contracts")
    print("Passed compose-deliverable evaluation acceptance fixtures")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Validate the reusable skill-evaluation contract and scaffold generator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "context-skills"
GENERATOR = ROOT / "skills" / "design-skill-evals" / "scripts" / "generate_eval_scaffold.py"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    profile = json.loads((EVAL / "skill-profile.json").read_text(encoding="utf-8"))
    plan = json.loads((EVAL / "eval-plan.json").read_text(encoding="utf-8"))
    tasks = [json.loads(line) for line in (EVAL / "cases" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if line]
    check(profile["schema_version"] == "ascent.skill-eval-profile.v1", "profile schema version changed")
    check(plan["coverage"]["mode"] == "regression", "context suite should protect established behavior")
    check({task["case_type"] for task in tasks} >= {"positive", "negative"}, "suite needs positive and negative cases")
    check(all(task["reference_solution"] for task in tasks), "task is missing a reference solution")
    check(all(task["trials"] == 1 for task in tasks), "deterministic fixture should run one trial")

    with tempfile.TemporaryDirectory(prefix="ascent-eval-scaffold-") as temp:
        output = Path(temp) / "generated"
        command = [sys.executable, str(GENERATOR), "--profile", str(EVAL / "skill-profile.json"), "--output", str(output), "--inspect"]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        check(result.returncode == 0, f"scaffold generation failed: {result.stderr}")
        generated_task = json.loads((output / "cases" / "tasks.jsonl").read_text(encoding="utf-8"))
        check(generated_task["expected_outcome"] == profile["success_conditions"], "scaffold did not preserve success conditions")
        check((output / "inspect" / "README.md").exists(), "Inspect adapter placeholder was not generated")
        repeat = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        check(repeat.returncode != 0, "generator overwrote an existing scaffold")

    poc = (ROOT / "evals" / "inspect-poc" / "context_skill_task.py").read_text(encoding="utf-8")
    dockerfile = (ROOT / "evals" / "inspect-poc" / "Dockerfile").read_text(encoding="utf-8")
    for expected in ("Task", "json_dataset", "react(", "includes()", 'sandbox="docker"'):
        check(expected in poc, f"Inspect POC does not map {expected}")
    check("verify_context_case.py" in dockerfile, "Inspect sandbox omits its verifier")

    print("Passed skill-evaluation acceptance fixtures")


if __name__ == "__main__":
    main()

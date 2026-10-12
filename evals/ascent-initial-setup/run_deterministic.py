#!/usr/bin/env python3
"""Hermetic regression checks for ascent-initial-setup routing and readiness."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[1]
SKILL = ROOT / "plugins" / "ascent" / "skills" / "ascent-initial-setup"
SHARED = ROOT / "plugins" / "ascent" / "shared" / "scripts"
PREPARE = SKILL / "scripts" / "prepare-project-folder.py"
SETUP = SKILL / "scripts" / "setup-workspace.py"
SYNC = SHARED / "sync.py"
STORAGE_CASES = EVAL_DIR / "cases" / "storage-decisions.json"
CHECKS_PER_RUN = 10

SITECUSTOMIZE = '''"""Deny network access in ascent-initial-setup eval subprocesses."""
import socket

class OfflineViolation(RuntimeError):
    pass

def blocked(*args, **kwargs):
    raise OfflineViolation("network access is blocked by the ascent-initial-setup eval")

class BlockedSocket(socket.socket):
    def __init__(self, *args, **kwargs):
        raise OfflineViolation("network access is blocked by the ascent-initial-setup eval")

socket.socket = BlockedSocket
socket.create_connection = blocked
socket.socketpair = blocked
socket.getaddrinfo = blocked
socket.gethostbyname = blocked
'''


def command(argv: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def require(result: subprocess.CompletedProcess[str], check_id: str) -> None:
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed without output"
        raise RuntimeError(f"{check_id}: {detail}")


def documentation_text() -> str:
    paths = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths).casefold()


def existing_yaml_parent() -> str | None:
    """Find an already-installed PyYAML without installing or accessing the network."""
    probes = [sys.executable]
    if Path("/usr/bin/python3").is_file() and "/usr/bin/python3" not in probes:
        probes.append("/usr/bin/python3")
    for interpreter in probes:
        result = subprocess.run(
            [interpreter, "-c", "import pathlib, yaml; print(pathlib.Path(yaml.__file__).parent.parent)"],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    return None


def run_once() -> list[str]:
    passed: list[str] = []
    docs = documentation_text()
    storage = json.loads(STORAGE_CASES.read_text(encoding="utf-8"))
    for case in storage["cases"]:
        missing = [concept for concept in case["required_concepts"] if concept.casefold() not in docs]
        if missing:
            raise RuntimeError(f"storage-{case['id']}: missing concepts: {missing}")
        passed.append(f"storage-{case['id']}")

    with tempfile.TemporaryDirectory(prefix="ascent-ascent-initial-setup-eval-") as temporary:
        temp = Path(temporary)
        home = temp / "home"
        account = temp / "account"
        site_dir = temp / "offline"
        home.mkdir()
        account.mkdir()
        site_dir.mkdir()
        (site_dir / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")
        python_paths = [str(site_dir)]
        yaml_parent = existing_yaml_parent()
        if yaml_parent:
            python_paths.append(yaml_parent)
        env = {
            **os.environ,
            "HOME": str(home),
            "PYTHONPATH": os.pathsep.join(python_paths),
            "PYTHONDONTWRITEBYTECODE": "1",
            "ASCENT_PROJECT_ROOT": str(account / "Eval Project"),
        }

        prepare = command(
            [sys.executable, str(PREPARE), "--mode", "new", "--account-root", str(account), "--project-name", "Eval Project"],
            ROOT,
            env,
        )
        require(prepare, "prepare-fresh-project")
        passed.append("prepare-fresh-project")

        project = account / "Eval Project"
        setup = command(
            [sys.executable, str(SETUP), "--project", str(project), "--account", "Eval Account", "--project-name", "Eval Project"],
            ROOT,
            env,
        )
        require(setup, "orchestrate-workspace")
        setup_output = (setup.stdout + "\n" + setup.stderr).casefold()
        if "readiness" not in setup_output and "ready" not in setup_output:
            raise RuntimeError("readiness-report-emitted: orchestrator output contains no readiness verdict")
        passed.extend(["orchestrate-workspace", "readiness-report-emitted"])

        expected = [
            project / "workspace" / ".system" / "project.yaml",
            project / "workspace" / ".system" / "search" / "index.sqlite",
            project / "workspace" / ".system" / "sync-state.json",
            project / "workspace" / "trackers" / "raid.xlsx",
            project / "workspace" / "trackers" / "stakeholders.xlsx",
        ]
        missing = [str(path.relative_to(project)) for path in expected if not path.is_file()]
        if missing:
            raise RuntimeError(f"workspace-artifacts-created: missing {missing}")
        passed.append("workspace-artifacts-created")

        identity = expected[0].read_text(encoding="utf-8")
        if "Eval Account" not in identity or "Eval Project" not in identity:
            raise RuntimeError("identity-values-recorded: project.yaml does not contain both identity values")
        passed.append("identity-values-recorded")

        ready = command([sys.executable, str(SYNC), "--check-setup"], project, env)
        require(ready, "complete-workspace-is-ready")
        if "not ready" in ready.stdout.casefold():
            raise RuntimeError("complete-workspace-is-ready: setup check reported not ready")
        passed.append("complete-workspace-is-ready")

        expected[0].unlink()
        incomplete = command([sys.executable, str(SYNC), "--check-setup"], project, env)
        if "not ready" not in incomplete.stdout.casefold():
            raise RuntimeError("missing-identity-is-not-ready: setup check accepted missing project.yaml")
        passed.append("missing-identity-is-not-ready")

    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="Whole-suite repeats.")
    parser.add_argument("--quiet", action="store_true", help="Only emit final JSON.")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    started = time.monotonic()
    completed = 0
    failed: list[str] = []
    check_ids: list[str] = []
    for attempt in range(1, args.runs + 1):
        try:
            check_ids = run_once()
            completed += 1
            if not args.quiet:
                print(f"PASS: run {attempt}/{args.runs} ({len(check_ids)} checks)")
        except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as error:
            failed.append(f"run-{attempt}: {error}")
            if not args.quiet:
                print(f"FAIL: run {attempt}/{args.runs}: {error}", file=sys.stderr)

    passed = not failed and completed == args.runs
    checks_per_run = len(check_ids) if check_ids else CHECKS_PER_RUN
    payload = {
        "suite": "ascent-initial-setup",
        "arm": "with-skills",
        "outcome": "pass" if passed else "fail",
        "checks_total": checks_per_run * args.runs,
        "checks_passed": checks_per_run * completed,
        "evaluated_task_count": 2,
        "outcome_pass_rate": completed / args.runs,
        "failed_check_ids": failed,
        "check_ids": check_ids,
        "harness_wall_clock_seconds": round(time.monotonic() - started, 3),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

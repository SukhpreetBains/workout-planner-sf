#!/usr/bin/env python3
"""Hermetic regression checks for workspace-collect.

Two graders run over synthetic fixtures:

- collection-contract: drives the shipped collect_inbox.py, manage-source-context.py
  and select_inbox_batch.py through plan, write, fail, and schedule against a
  fresh temporary Project, and checks the files and state they leave.
- trajectory-contract: runs grade_trajectory.py over synthetic Codex session
  logs, one clean and one with every forbidden behavior, so the log grader is
  itself proven before it is trusted on real runs.

The whole suite repeats `--runs` times. Inbox files are hashed per run and
compared after one declared normalisation (the `collected_at` timestamp).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[1]
SHARED = ROOT / "plugins" / "ascent" / "shared" / "scripts"
COLLECT = SHARED / "collect_inbox.py"
SELECT = SHARED / "select_inbox_batch.py"
SOURCE_CONTEXT = ROOT / "plugins" / "ascent" / "skills" / "ascent-initial-setup" / "scripts" / "manage-source-context.py"
CONTRACTS = ROOT / "plugins" / "ascent" / "skills" / "workspace-collect" / "contracts"
GRADER = EVAL_DIR / "grade_trajectory.py"
FIXTURE = EVAL_DIR / "cases" / "collection-fixture.json"
TRAJECTORIES = EVAL_DIR / "cases" / "trajectories"
EXPECTED_VIOLATIONS = {
    "connector-search", "tool-not-in-contract", "browser-or-desktop-tool",
    "schedule-changed-in-scheduled-run", "workspace-add-step", "inbox-file-changed",
}
NORMALISE = [("collected-at-timestamp", re.compile(r"^collected_at: .*$", re.MULTILINE), "collected_at: <normalised>")]

SITECUSTOMIZE = '''"""Deny network access in workspace-collect eval subprocesses."""
import socket

class OfflineViolation(RuntimeError):
    pass

def blocked(*args, **kwargs):
    raise OfflineViolation("network access is blocked by the workspace-collect eval")

class BlockedSocket(socket.socket):
    def __init__(self, *args, **kwargs):
        raise OfflineViolation("network access is blocked by the workspace-collect eval")

socket.socket = BlockedSocket
socket.create_connection = blocked
socket.socketpair = blocked
socket.getaddrinfo = blocked
socket.gethostbyname = blocked
'''


def yaml_parent() -> str:
    """Find an installed PyYAML without installing or using the network."""
    probes = [sys.executable] + [p for p in ("/usr/bin/python3",) if Path(p).is_file()]
    for interpreter in probes:
        result = subprocess.run([interpreter, "-c", "import pathlib, yaml; print(pathlib.Path(yaml.__file__).parent.parent)"],
                                text=True, capture_output=True, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
    raise RuntimeError("PyYAML is not installed for this interpreter; run with the Ascent cached environment's Python")


class Run:
    def __init__(self, temp: Path, fixture: dict):
        self.temp = temp
        self.fixture = fixture
        self.project = temp / "Project"
        self.system = self.project / "workspace" / ".system"
        self.inbox = self.project / "workspace" / "inbox"
        self.system.mkdir(parents=True)
        self.inbox.mkdir(parents=True)
        for name in ("project", "trackers"):
            (self.project / "workspace" / name).mkdir()
        offline = temp / "offline"
        offline.mkdir()
        (offline / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")
        (temp / "home").mkdir()
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(temp / "home"),
            "TMPDIR": str(temp),
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "PYTHONPATH": os.pathsep.join([str(offline), yaml_parent()]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "ASCENT_PROJECT_ROOT": str(self.project),
        }
        if self.env["PYTHONPATH"].split(os.pathsep)[-1] not in sys.path:
            sys.path.append(self.env["PYTHONPATH"].split(os.pathsep)[-1])
        import yaml  # noqa: PLC0415 - only after yaml_parent() proved it exists
        self.yaml = yaml
        (self.system / "source-context.yaml").write_text(yaml.safe_dump(fixture["source_context"], sort_keys=False), encoding="utf-8")

    def call(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(script), *args], cwd=self.project, env=self.env,
                              text=True, capture_output=True, check=False)

    def json(self, script: Path, *args: str) -> dict:
        result = self.call(script, *args)
        if result.returncode:
            raise RuntimeError(f"{script.name} {' '.join(args[:1])}: {result.stderr.strip() or result.stdout.strip()}")
        return json.loads(result.stdout)

    def write(self, payload: dict, name: str = "payload.json") -> subprocess.CompletedProcess[str]:
        path = self.temp / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return self.call(COLLECT, "write", "--input", str(path))

    def state(self) -> dict:
        return self.yaml.safe_load((self.system / "collection-state.yaml").read_text(encoding="utf-8"))

    def inbox_files(self) -> list[Path]:
        return sorted(p for p in self.inbox.iterdir() if p.is_file())


def check(condition: bool, check_id: str, detail: str = "") -> str:
    if not condition:
        raise RuntimeError(f"{check_id}: {detail}" if detail else check_id)
    return check_id


def collection_checks(run: Run) -> list[str]:
    fixture = run.fixture
    sentinels = fixture["sentinels"]
    passed: list[str] = []

    plan = run.json(COLLECT, "plan", "--contracts-dir", str(CONTRACTS), "--since", fixture["start"])
    planned = [s["id"] for s in plan["sources"]]
    passed.append(check(planned == fixture["expected_plan"]["sources"], "plan-only-collect-sources", f"got {planned}"))
    skipped = {s["id"]: s["skipped"] for s in plan["skipped"]}
    reasons_ok = all(reason in skipped.get(source, "") for source, reason in fixture["expected_plan"]["skipped"].items())
    passed.append(check(reasons_ok and len(skipped) == len(fixture["expected_plan"]["skipped"]), "plan-skips-disabled-and-uncontracted", f"got {skipped}"))
    passed.append(check("slack-not-collected" not in planned + list(skipped), "plan-ignores-unmarked-locations"))

    schedule = run.json(COLLECT, "schedule", "--frequency", "weekly", "--weekday", "tuesday", "--time", "09:00",
                        "--timezone", "America/New_York", "--host", "eval", "--task-id", "eval-task")
    passed.append(check(schedule["cursors_started"] == [], "schedule-keeps-existing-cursors", f"started {schedule['cursors_started']}"))

    by_id = {item["id"]: item for item in fixture["slack_runs"]}
    for slack_run in fixture["slack_runs"]:
        documents = by_id[slack_run["same_as"]]["documents"] if "same_as" in slack_run else slack_run["documents"]
        before = set(run.inbox_files())
        result = run.write({"source_id": "slack-pod", "documents": documents})
        if result.returncode:
            raise RuntimeError(f"slack-{slack_run['id']}: {result.stderr.strip()}")
        output = json.loads(result.stdout)
        expect = slack_run["expect"]
        new_files = sorted(set(run.inbox_files()) - before)
        passed.append(check(len(output["files"]) == expect["files"] == len(new_files) and output["cursor"] == expect["cursor"],
                            f"slack-{slack_run['id']}-files-and-cursor", f"files {output['files']} cursor {output['cursor']}"))
        if "outcome" in expect:
            outcome = run.state()["sources"]["slack-pod"]["last_result"]["outcome"]
            passed.append(check(outcome == expect["outcome"], f"slack-{slack_run['id']}-outcome", outcome))
        text = "\n".join(path.read_text(encoding="utf-8") for path in new_files)
        missing = [phrase for phrase in expect.get("contains", []) if phrase not in text]
        present = [phrase for phrase in expect.get("excludes", []) if phrase in text]
        if expect.get("contains") or expect.get("excludes"):
            passed.append(check(not missing and not present, f"slack-{slack_run['id']}-content", f"missing {missing} present {present}"))
        for path in new_files:
            front = run.yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])
            passed.append(check(front.get("collected_by") == "workspace-collect" and front.get("source_id") == "slack-pod",
                                f"slack-{slack_run['id']}-front-matter"))

    teams = fixture["teams_run"]
    before = set(run.inbox_files())
    result = run.write({"source_id": "teams-standup", "documents": teams["documents"]})
    output = json.loads(result.stdout) if result.returncode == 0 else {}
    new_files = sorted(set(run.inbox_files()) - before)
    passed.append(check(len(new_files) == teams["expect"]["files"] and output.get("cursor") == teams["expect"]["cursor"],
                        "teams-transcript-files-and-cursor", f"{output}"))
    transcript = new_files[0].read_text(encoding="utf-8") if new_files else ""
    passed.append(check(f"[{teams['expect']['first_line_time']}] **Avery Stone:**" in transcript, "teams-transcript-real-times",
                        "first cue is not shown at its wall-clock time"))
    repeat = run.write({"source_id": "teams-standup", "documents": teams["documents"]})
    passed.append(check(repeat.returncode == 0 and json.loads(repeat.stdout)["files"] == [], "teams-transcript-not-collected-twice"))

    written = [p for p in run.project.rglob("*") if p.is_file() and p.name != "source-context.yaml"]
    leaks = [str(p.relative_to(run.project)) for p in written if sentinels["passcode"] in p.read_text(encoding="utf-8", errors="ignore")]
    passed.append(check(not leaks, "passcode-never-written", f"found in {leaks}"))
    state_text = "".join((run.system / name).read_text(encoding="utf-8") for name in ("collection-state.yaml", "collection.yaml"))
    passed.append(check(sentinels["message_text"] not in state_text, "message-text-not-in-state"))
    partials = [p.name for p in run.inbox.iterdir() if p.name.endswith(".partial")]
    passed.append(check(not partials, "no-partial-files-left", f"{partials}"))

    cursor = run.state()["sources"]["teams-standup"]["cursor"]
    failed = run.json(COLLECT, "fail", "--source-id", "teams-standup", "--reason", "Needs reconnecting")
    passed.append(check(failed["cursor"] == cursor and run.state()["sources"]["teams-standup"]["last_result"]["outcome"] == "failed",
                        "failure-keeps-cursor"))

    count = len(run.inbox_files())
    refused = run.write({"source_id": "slack-not-collected", "documents": fixture["slack_runs"][0]["documents"]})
    passed.append(check(refused.returncode != 0 and len(run.inbox_files()) == count, "unmarked-source-refused"))
    bad = run.write({"source_id": "slack-pod", "documents": [{"entries": [
        {"id": "x1", "at": "2026-10-21T10:00:00Z", "author": "E", "text": "valid"},
        {"id": "x2", "author": "E", "text": "no timestamp"}]}]})
    passed.append(check(bad.returncode != 0 and len(run.inbox_files()) == count, "bad-timestamp-writes-nothing"))

    (run.inbox / "notes-from-user.txt").write_text("Dropped in by the user.", encoding="utf-8")
    batch = run.json(SELECT)
    collected = {Path(item["path"]).name for item in batch["collected"]}
    expected = {p.name for p in run.inbox_files() if p.suffix == ".md"}
    passed.append(check(collected == expected and "notes-from-user.txt" not in collected, "selector-reports-collected-files",
                        f"{collected} vs {expected}"))

    run.json(COLLECT, "unschedule")
    status = run.json(COLLECT, "status")
    passed.append(check(status["schedule"] is None and status["sources"]["slack-pod"]["cursor"] == "2026-10-20T09:15:00.000000Z",
                        "unschedule-keeps-cursors"))

    record_root = run.temp / "record"
    record_root.mkdir()
    init = run.call(SOURCE_CONTEXT, "init", "--root", str(record_root), "--account", "A", "--project", "P")
    upsert = run.call(SOURCE_CONTEXT, "upsert-source", "--root", str(record_root), "--id", "teams-x", "--kind", "teams",
                      "--name", "Standup", "--locator", f"https://teams.microsoft.com/meet/1?p={sentinels['passcode']}",
                      "--identifier", "online_meeting_id=M", "--location-type", "meeting_series", "--purpose", "standup", "--collect")
    passed.append(check(init.returncode == 0 and upsert.returncode != 0, "source-record-refuses-passcode"))
    return passed


def trajectory_checks(run: Run) -> list[str]:
    passed: list[str] = []
    clean = run.call(GRADER, str(TRAJECTORIES / "clean-scheduled-run.jsonl"))
    clean_out = json.loads(clean.stdout)
    passed.append(check(clean.returncode == 0 and clean_out["graded_runs"] == 1 and clean_out["outcome"] == "pass",
                        "trajectory-clean-run-passes", f"{clean_out.get('runs')}"))
    passed.append(check(clean_out["runs"][0]["tokens"]["total_tokens"] == 3000, "trajectory-tokens-reported"))
    bad = run.call(GRADER, str(TRAJECTORIES / "violating-scheduled-run.jsonl"))
    bad_out = json.loads(bad.stdout)
    kinds = {violation.split(":", 1)[0] for violation in bad_out["runs"][0]["violations"]}
    passed.append(check(bad.returncode != 0 and kinds == EXPECTED_VIOLATIONS, "trajectory-violations-all-detected",
                        f"missing {sorted(EXPECTED_VIOLATIONS - kinds)} extra {sorted(kinds - EXPECTED_VIOLATIONS)}"))
    return passed


def artifact_digests(run: Run) -> tuple[str, str]:
    raw, normalised = hashlib.sha256(), hashlib.sha256()
    for path in run.inbox_files():
        text = path.read_text(encoding="utf-8")
        raw.update(path.name.encode() + b"\0" + text.encode())
        for _, pattern, replacement in NORMALISE:
            text = pattern.sub(replacement, text)
        normalised.update(path.name.encode() + b"\0" + text.encode())
    return raw.hexdigest(), normalised.hexdigest()


def run_once(fixture: dict) -> tuple[list[str], tuple[str, str]]:
    with tempfile.TemporaryDirectory(prefix="ascent-workspace-collect-eval-") as temporary:
        run = Run(Path(temporary), fixture)
        passed = collection_checks(run)
        digests = artifact_digests(run)
        passed += trajectory_checks(run)
        return passed, digests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=3, help="Whole-suite repeats.")
    parser.add_argument("--quiet", action="store_true", help="Only emit final JSON.")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    started = time.monotonic()
    completed, failed, check_ids, digests = 0, [], [], []
    for attempt in range(1, args.runs + 1):
        try:
            check_ids, digest = run_once(fixture)
            digests.append(digest)
            completed += 1
            if not args.quiet:
                print(f"PASS: run {attempt}/{args.runs} ({len(check_ids)} checks)")
        except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError, KeyError, IndexError) as error:
            failed.append(f"run-{attempt}: {error}")
            if not args.quiet:
                print(f"FAIL: run {attempt}/{args.runs}: {error}", file=sys.stderr)
    identical_raw = len({d[0] for d in digests}) <= 1
    identical_normalised = len({d[1] for d in digests}) <= 1
    if digests and not identical_normalised:
        failed.append("determinism: inbox artifacts differ after the declared normalisation")
    passed = not failed and completed == args.runs
    payload = {
        "suite": "workspace-collect",
        "arm": "with-skills",
        "outcome": "pass" if passed else "fail",
        "checks_total": len(check_ids) * args.runs,
        "checks_passed": len(check_ids) * completed,
        "evaluated_task_count": 4,
        "outcome_pass_rate": completed / args.runs,
        "failed_check_ids": failed,
        "check_ids": check_ids,
        "determinism": {
            "runs": len(digests),
            "identical_before_normalisation": identical_raw,
            "identical_after_declared_normalisation": identical_normalised,
            "canonical_artifact_sha256": digests[0][1] if digests else None,
            "declared_normalisation": [rule for rule, _, _ in NORMALISE],
        },
        "harness_wall_clock_seconds": round(time.monotonic() - started, 3),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

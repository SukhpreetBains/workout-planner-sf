#!/usr/bin/env python3
"""Serve the local, allowlisted skill-evaluation workbench.

Safety properties, unchanged from the first version of this server:

* One allowlisted suite. Any other suite id is refused.
* The browser cannot supply a command, model, file path, fixture or prompt. The
  only request parameter accepted anywhere is an integer run-history limit.
* Every run executes one fixed runner path in a subprocess under a timeout, and
  the runner builds its own fresh temporary workspace.
* Results are written under ``evals/<suite-id>/results/``, which is Git-ignored.

Cost, time and consistency numbers are not computed here. They come from the
telemetry CLI under ``evals/lib/`` (owned by a separate work stream):

    python3 -m evals.lib.aggregate     --suite <suite-id>
    python3 -m evals.lib.telemetry     --session <path> --out <file>
    python3 -m evals.lib.emit_summary  --suite <suite-id>

When that CLI is absent, the endpoints report the absence and the reason. They
never substitute a placeholder number.

Endpoints
---------
GET  /api/suite/<suite-id>              suite plan, taxonomy and task contracts
GET  /api/runs/<suite-id>?limit=k       run history, newest first
GET  /api/summary/<suite-id>            aggregate summary + telemetry availability
GET  /api/paste/<suite-id>              the harness's paste-ready workflow block
GET  /api/results/<suite-id>            the latest run record only
POST /api/run/<suite-id>                run the suite once
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

SUITE_ID = "context-skills"
SUITE_DIR = ROOT / "evals" / SUITE_ID
RUNNER = SUITE_DIR / "run_deterministic.py"
TASKS_FILE = SUITE_DIR / "cases" / "tasks.jsonl"
PLAN_FILE = SUITE_DIR / "eval-plan.json"
RESULTS_DIR = SUITE_DIR / "results"
RUNS_DIR = RESULTS_DIR / "runs"
SUMMARY_FILE = RESULTS_DIR / "latest.json"
BASELINE_FILE = SUITE_DIR / "human-baseline.json"

RUN_TIMEOUT_SECONDS = 90
CLI_TIMEOUT_SECONDS = 60
RUN_LOCK = threading.Lock()

AGGREGATE_MODULE = "evals.lib.aggregate"
TELEMETRY_MODULE = "evals.lib.telemetry"
EMIT_MODULE = "evals.lib.emit_summary"
AGGREGATE_COMMAND = f"python3 -m {AGGREGATE_MODULE} --suite {SUITE_ID}"
TELEMETRY_COMMAND = f"python3 -m {TELEMETRY_MODULE} --session <path> --out <file>"

RUN_RECORD_SCHEMA = "ascent.eval-run-record.v1"
SUITE_SUMMARY_SCHEMA = "ascent.eval-suite-summary.v1"
DEFAULT_ARM = "with-skills"
COMPARISON_ARM = "baseline-no-skills"

# Provisional, from docs/sgaf-717-evals-redesign-spec.md. Recorded here so the
# page can state the thresholds it is judging against rather than implying them.
CONSISTENCY_THRESHOLDS = {
    "measure": "coefficient of variation of total tokens across runs in one arm",
    "status": "provisional",
    "bands": [
        {"verdict": "predictable", "range": "< 0.10", "reading": "Cost per run is safe to quote to a client."},
        {"verdict": "variable", "range": "0.10 - 0.30", "reading": "Budget with headroom; investigate the spread."},
        {"verdict": "unpredictable", "range": "> 0.30", "reading": "Do not quote a per-run cost; the workflow is not stable."},
    ],
}

NO_MODEL_REASON = (
    "This suite executes deterministic Python scripts in a subprocess. No model is in "
    "the loop, so there are no tokens, no dollars and no session transcript to parse. "
    "Token and dollar figures start being real when an agent-driven suite is added."
)
NO_BASELINE_REASON = (
    "No human baseline has been recorded for this deliverable. A baseline is a measured "
    "or stated figure from a person who has done the same work; it is never derived from "
    "the agent's own run."
)
NO_COMPARISON_ARM_REASON = (
    f"No {COMPARISON_ARM} runs exist for this suite. The comparison arm needs the same "
    "task attempted without the Ascent skills, which requires a model-driven suite; a "
    "deterministic script harness has no meaningful no-skills arm."
)
NO_GOLDEN_REASON = (
    "This suite has no reference document, so there is nothing to compare the output "
    "against section by section. Its checks are code-based assertions on generated "
    "artifacts."
)
NO_BEHAVIOR_REASON = (
    "Skill invocations, turns and clarifying questions are read from an agent session "
    "transcript. The deterministic runner does not produce one."
)

# Fallback wording, used only when the suite plan does not supply its own. The plan
# is the suite owner's account of what is not measured and why, so it wins.
FALLBACK_REASONS = {
    "cost": NO_MODEL_REASON,
    "human_baseline_minutes": NO_BASELINE_REASON,
    "comparison_arm": NO_COMPARISON_ARM_REASON,
    "golden_comparison": NO_GOLDEN_REASON,
    "behavior": NO_BEHAVIOR_REASON,
    "consistency": NO_MODEL_REASON,
}


def plan_reason(key: str) -> str:
    """Why a block is absent, in the suite plan's own words where it has them."""
    try:
        plan = suite_plan()
    except (OSError, json.JSONDecodeError):
        return FALLBACK_REASONS.get(key, "Not measured.")
    questions = plan.get("questions") or {}
    gaps = {gap.get("id"): gap for gap in (plan.get("gaps") or []) if isinstance(gap, dict)}

    def question_note(name: str) -> Optional[str]:
        block = questions.get(name) or {}
        return block.get("note") or None

    def gap_text(gap_id: str) -> Optional[str]:
        gap = gaps.get(gap_id) or {}
        statement = gap.get("statement")
        if not statement:
            return None
        unblocked = gap.get("unblocked_by")
        return statement + (" Unblocked by: " + unblocked if unblocked else "")

    if key == "cost":
        return question_note("cost") or gap_text("no-cost-data") or FALLBACK_REASONS[key]
    if key == "human_baseline_minutes":
        return gap_text("no-human-baseline") or question_note("time") or FALLBACK_REASONS[key]
    if key == "comparison_arm":
        arm = (plan.get("arms") or {}).get(COMPARISON_ARM) or {}
        note = arm.get("note")
        if note:
            unblocked = arm.get("unblocked_by")
            return note + (" Unblocked by: " + unblocked if unblocked else "")
        return gap_text("no-baseline-arm") or FALLBACK_REASONS[key]
    if key == "golden_comparison":
        return gap_text("no-golden-reference") or FALLBACK_REASONS[key]
    if key == "behavior":
        return gap_text("behavior-not-observable") or FALLBACK_REASONS[key]
    if key == "consistency":
        note = (plan.get("consistency") or {}).get("note")
        return note or gap_text("consistency-unknown") or FALLBACK_REASONS[key]
    return FALLBACK_REASONS.get(key, "Not measured.")


def consistency_thresholds() -> dict:
    """The provisional bands, preferring the suite plan's recorded copy."""
    thresholds = dict(CONSISTENCY_THRESHOLDS)
    try:
        plan = suite_plan()
    except (OSError, json.JSONDecodeError):
        return thresholds
    block = plan.get("consistency") or {}
    bands = block.get("thresholds") or {}
    if bands:
        readings = {band["verdict"]: band["reading"] for band in CONSISTENCY_THRESHOLDS["bands"]}
        thresholds["bands"] = [
            {"verdict": verdict, "range": bands[verdict], "reading": readings.get(verdict, "")}
            for verdict in ("predictable", "variable", "unpredictable")
            if verdict in bands
        ]
    if block.get("metric"):
        thresholds["measure"] = block["metric"]
    if block.get("thresholds_status"):
        thresholds["status"] = block["thresholds_status"]
    if block.get("note"):
        thresholds["note"] = block["note"]
    return thresholds


# --------------------------------------------------------------------------- io


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def suite_tasks() -> list:
    lines = TASKS_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def suite_plan() -> dict:
    return read_json(PLAN_FILE)


def suite_payload() -> dict:
    tasks = suite_tasks()
    plan = suite_plan()
    return {
        "suite_id": SUITE_ID,
        "plan": plan,
        "taxonomy": plan.get("taxonomy", {}),
        "tasks": tasks,
        "checks_total": len(tasks),
        "runner": str(RUNNER.relative_to(ROOT)),
        "run_timeout_seconds": RUN_TIMEOUT_SECONDS,
        "arms": {"recorded": DEFAULT_ARM, "comparison": COMPARISON_ARM},
        "consistency_thresholds": consistency_thresholds(),
    }


def load_runs(limit: Optional[int] = None) -> dict:
    if not RUNS_DIR.exists():
        return {
            "runs": [],
            "total_recorded": 0,
            "reason": "No run has been recorded yet. Results appear here after the first run.",
        }
    records = []
    unreadable = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        try:
            record = read_json(path)
        except (OSError, json.JSONDecodeError):
            unreadable.append(path.name)
            continue
        if isinstance(record, dict) and record.get("schema_version") == RUN_RECORD_SCHEMA:
            records.append(record)
        else:
            unreadable.append(path.name)
    records.sort(key=lambda item: str(item.get("started_at", "")), reverse=True)
    total = len(records)
    if limit is not None:
        records = records[:limit]
    payload = {"runs": records, "total_recorded": total}
    if unreadable:
        payload["unreadable_files"] = unreadable
    if total == 0:
        payload["reason"] = "No run has been recorded yet. Results appear here after the first run."
    return payload


def write_run_record(record: dict) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    target = RUNS_DIR / f"{record['run_id']}.json"
    temporary = RUNS_DIR / f".{record['run_id']}.tmp"
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def next_run_id(stamp: str) -> str:
    existing = 0
    if RUNS_DIR.exists():
        existing = len(list(RUNS_DIR.glob(f"{SUITE_ID}-{stamp}-*.json")))
    return f"{SUITE_ID}-{stamp}-{existing + 1:02d}"


# ------------------------------------------------------------------- telemetry


def module_available(module: str) -> bool:
    probe = (
        "import importlib.util, sys\n"
        "try:\n"
        f"    spec = importlib.util.find_spec({module!r})\n"
        "except Exception:\n"
        "    spec = None\n"
        "sys.exit(0 if spec else 1)\n"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", probe], cwd=ROOT, capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def last_json_object(text: str) -> Optional[dict]:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            return candidate
    try:
        candidate = json.loads(text)
    except json.JSONDecodeError:
        return None
    return candidate if isinstance(candidate, dict) else None


def aggregate_cli() -> tuple:
    """Ask evals.lib.aggregate for the suite summary. Returns (summary, meta)."""
    meta = {"command": AGGREGATE_COMMAND, "available": False}
    if not module_available(AGGREGATE_MODULE):
        meta["reason"] = (
            f"The telemetry CLI is not installed yet. `{AGGREGATE_COMMAND}` reports no "
            f"module named {AGGREGATE_MODULE}."
        )
        return None, meta
    try:
        completed = subprocess.run(
            [sys.executable, "-m", AGGREGATE_MODULE, "--suite", SUITE_ID],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        meta["reason"] = f"`{AGGREGATE_COMMAND}` exceeded {CLI_TIMEOUT_SECONDS} seconds."
        return None, meta
    except OSError as error:
        meta["reason"] = f"`{AGGREGATE_COMMAND}` could not be started: {error}"
        return None, meta
    meta["available"] = True
    meta["exit_code"] = completed.returncode
    if completed.returncode != 0:
        meta["reason"] = f"`{AGGREGATE_COMMAND}` exited {completed.returncode}."
        meta["stderr"] = completed.stderr.strip()[:2000]
        return None, meta
    payload = last_json_object(completed.stdout)
    if isinstance(payload, dict) and isinstance(payload.get("summary"), dict):
        payload = payload["summary"]
    if not isinstance(payload, dict) or "arms" not in payload:
        # The documented invocation writes the summary to results/latest.json rather
        # than to stdout, so read back the file the command just refreshed.
        payload = summary_file()
    if not isinstance(payload, dict) or "arms" not in payload:
        meta["reason"] = f"`{AGGREGATE_COMMAND}` exited 0 but produced no {SUITE_SUMMARY_SCHEMA} document."
        meta["stdout"] = completed.stdout.strip()[:2000]
        return None, meta
    return payload, meta


def summary_file() -> Optional[dict]:
    if not SUMMARY_FILE.exists():
        return None
    try:
        payload = read_json(SUMMARY_FILE)
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict) and payload.get("schema_version") == SUITE_SUMMARY_SCHEMA:
        return payload
    return None


def session_telemetry(run_id: Optional[str] = None) -> tuple:
    """Extract cost/time for one run from a session transcript, if one is configured.

    The transcript path comes from the ASCENT_EVAL_SESSION environment variable on
    the machine running the server. It is never accepted from the browser.
    """
    meta = {"command": TELEMETRY_COMMAND, "available": False}
    session = os.environ.get("ASCENT_EVAL_SESSION", "").strip()
    if not session:
        meta["reason"] = (
            "No session transcript is configured. Set ASCENT_EVAL_SESSION to a host "
            "session file to have this server extract tokens and dollars for a run."
        )
        return None, meta
    if not module_available(TELEMETRY_MODULE):
        meta["reason"] = f"The telemetry CLI is not installed yet: no module named {TELEMETRY_MODULE}."
        return None, meta
    with tempfile.TemporaryDirectory(prefix="ascent-telemetry-") as temp:
        destination = Path(temp) / "telemetry.json"
        command = [
            sys.executable,
            "-m",
            TELEMETRY_MODULE,
            "--session",
            session,
            "--out",
            str(destination),
            "--suite",
            SUITE_ID,
            "--arm",
            DEFAULT_ARM,
        ]
        if run_id:
            command.extend(["--run-id", run_id])
        baseline = human_baseline()
        if baseline:
            command.extend(["--human-baseline-minutes", str(baseline["minutes"])])
            if baseline.get("source"):
                command.extend(["--human-baseline-source", baseline["source"]])
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            meta["reason"] = f"`{TELEMETRY_COMMAND}` failed: {error}"
            return None, meta
        meta["exit_code"] = completed.returncode
        if completed.returncode != 0:
            meta["reason"] = f"`{TELEMETRY_COMMAND}` exited {completed.returncode}."
            meta["stderr"] = completed.stderr.strip()[:2000]
            return None, meta
        payload = None
        if destination.exists():
            try:
                payload = read_json(destination)
            except (OSError, json.JSONDecodeError):
                payload = None
        if payload is None:
            payload = last_json_object(completed.stdout)
    if not isinstance(payload, dict):
        meta["reason"] = f"`{TELEMETRY_COMMAND}` produced no JSON telemetry object."
        return None, meta
    meta["available"] = True
    meta["session_path"] = session
    return payload, meta


def paste_block() -> dict:
    """Ask the harness for its paste-ready block. The page never invents this text."""
    command = f"python3 -m {EMIT_MODULE} --suite {SUITE_ID}"
    meta: dict = {"command": command, "available": False, "markdown": None}
    if not module_available(EMIT_MODULE):
        meta["reason"] = f"The telemetry CLI is not installed yet: no module named {EMIT_MODULE}."
        return meta
    try:
        completed = subprocess.run(
            [sys.executable, "-m", EMIT_MODULE, "--suite", SUITE_ID],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        meta["reason"] = f"`{command}` failed: {error}"
        return meta
    meta["exit_code"] = completed.returncode
    if completed.returncode != 0 or not completed.stdout.strip():
        meta["reason"] = (
            f"`{command}` exited {completed.returncode}. "
            + (completed.stderr.strip()[:600] or "No output.")
        )
        return meta
    meta["available"] = True
    meta["markdown"] = completed.stdout.rstrip()
    return meta


def human_baseline() -> Optional[dict]:
    """Return a recorded human baseline, or None. Never derived from a run."""
    minutes = os.environ.get("ASCENT_HUMAN_BASELINE_MINUTES", "").strip()
    if minutes:
        try:
            value = float(minutes)
        except ValueError:
            value = None
        if value is not None and value > 0:
            source = os.environ.get("ASCENT_HUMAN_BASELINE_SOURCE", "").strip()
            return {"minutes": value, "source": source or "ASCENT_HUMAN_BASELINE_MINUTES environment variable"}
    if BASELINE_FILE.exists():
        try:
            payload = read_json(BASELINE_FILE)
        except (OSError, json.JSONDecodeError):
            return None
        if isinstance(payload, dict):
            value = payload.get("human_baseline_minutes")
            if isinstance(value, (int, float)) and value > 0:
                return {
                    "minutes": float(value),
                    "source": payload.get("human_baseline_source") or str(BASELINE_FILE.relative_to(ROOT)),
                }
    return None


# ---------------------------------------------------------------- aggregation


def percentile(values: list, fraction: float) -> Optional[float]:
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return float(ordered[0])
    position = fraction * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return float(ordered[low]) * (1 - weight) + float(ordered[high]) * weight


def coefficient_of_variation(values: list) -> Optional[float]:
    if len(values) < 2:
        return None
    mean = statistics.fmean(values)
    if mean == 0:
        return None
    return statistics.stdev(values) / mean


def consistency_verdict(cv: Optional[float]) -> Optional[str]:
    if cv is None:
        return None
    if cv < 0.10:
        return "predictable"
    if cv <= 0.30:
        return "variable"
    return "unpredictable"


def spread(values: list, with_cv: bool = False) -> Optional[dict]:
    if not values:
        return None
    block = {
        "min": min(values),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": max(values),
        "mean": statistics.fmean(values),
        "n": len(values),
    }
    if with_cv:
        block["coefficient_of_variation"] = coefficient_of_variation(values)
    return block


def measured(record: dict, block: str, key: str) -> Optional[float]:
    section = record.get(block)
    if not isinstance(section, dict):
        return None
    value = section.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def fallback_summary(runs: list) -> Optional[dict]:
    """Summarise the run records this workbench recorded.

    Used only when evals.lib.aggregate is unavailable. Every figure comes from a
    measured field on a run record; blocks with no measurements are omitted with
    a reason rather than zero-filled.
    """
    if not runs:
        return None
    arms: dict = {}
    for record in runs:
        arms.setdefault(record.get("arm") or "unrecorded", []).append(record)

    summary = {
        "schema_version": SUITE_SUMMARY_SCHEMA,
        "suite_id": SUITE_ID,
        "generated_at": iso_now(),
        "runs_per_arm": max(len(group) for group in arms.values()),
        "arms": {},
        "computed_by": "workbench-fallback",
    }
    for arm, group in sorted(arms.items()):
        outcomes = [str(item.get("correctness", {}).get("outcome", "")) for item in group]
        graded = [value for value in outcomes if value in {"pass", "fail"}]
        tokens = [value for value in (measured(item, "cost", "total_tokens") for item in group) if value is not None]
        dollars = [value for value in (measured(item, "cost", "estimated_usd") for item in group) if value is not None]
        seconds = [
            value
            for value in (measured(item, "time", "agent_wall_clock_seconds") for item in group)
            if value is not None
        ]
        block: dict = {"run_count": len(group)}
        if graded:
            block["correctness_pass_rate"] = graded.count("pass") / len(graded)
        token_spread = spread(tokens, with_cv=True)
        if token_spread:
            block["total_tokens"] = token_spread
            cv = token_spread.get("coefficient_of_variation")
            verdict = consistency_verdict(cv)
            if verdict:
                block["consistency_verdict"] = verdict
            else:
                block["consistency_unavailable_reason"] = (
                    "A spread needs at least two runs with token telemetry in the same arm."
                )
        else:
            block["consistency_unavailable_reason"] = plan_reason("consistency")
        dollar_spread = spread(dollars)
        if dollar_spread:
            block["estimated_usd"] = dollar_spread
        wall_spread = spread(seconds, with_cv=True)
        if wall_spread:
            block["wall_clock_seconds"] = wall_spread
        summary["arms"][arm] = block

    left = summary["arms"].get(DEFAULT_ARM, {})
    right = summary["arms"].get(COMPARISON_ARM, {})
    deltas: dict = {}
    for key, source in (("tokens_saved_p50", "total_tokens"), ("usd_saved_p50", "estimated_usd")):
        if source in left and source in right:
            deltas[key] = right[source]["p50"] - left[source]["p50"]
    if "wall_clock_seconds" in left and "wall_clock_seconds" in right:
        deltas["minutes_saved_p50"] = (right["wall_clock_seconds"]["p50"] - left["wall_clock_seconds"]["p50"]) / 60
    if "correctness_pass_rate" in left and "correctness_pass_rate" in right:
        deltas["correctness_pass_rate_delta"] = left["correctness_pass_rate"] - right["correctness_pass_rate"]
    if deltas:
        summary["deltas"] = deltas
    else:
        summary["deltas_unavailable_reason"] = plan_reason("comparison_arm")
    return summary


def summary_payload() -> dict:
    runs = load_runs()["runs"]
    aggregate, aggregate_meta = aggregate_cli()
    _, extractor_meta = session_telemetry()
    source = None
    summary = aggregate
    if summary is not None:
        source = AGGREGATE_MODULE
    else:
        summary = summary_file()
        if summary is not None:
            source = str(SUMMARY_FILE.relative_to(ROOT))
        else:
            summary = fallback_summary(runs)
            if summary is not None:
                source = "workbench-fallback"
    payload = {
        "suite_id": SUITE_ID,
        "summary": summary,
        "source": source,
        "consistency_thresholds": consistency_thresholds(),
        "telemetry": {"aggregate": aggregate_meta, "extractor": extractor_meta},
        "unmeasured": {
            "cost": plan_reason("cost"),
            "human_baseline_minutes": plan_reason("human_baseline_minutes"),
            "comparison_arm": plan_reason("comparison_arm"),
            "consistency": plan_reason("consistency"),
            "golden_comparison": plan_reason("golden_comparison"),
            "behavior": plan_reason("behavior"),
        },
        "runs_considered": len(runs),
    }
    return payload


# ---------------------------------------------------------------------- runner


def run_suite() -> dict:
    started_monotonic = time.monotonic()
    started_at = iso_now()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = next_run_id(stamp)
    timed_out = False
    try:
        process = subprocess.run(
            [sys.executable, str(RUNNER)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=RUN_TIMEOUT_SECONDS,
            check=False,
        )
        stdout, stderr, exit_code = process.stdout, process.stderr, process.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = error.stdout or ""
        stderr = (error.stderr or "") + f"\nRunner exceeded the {RUN_TIMEOUT_SECONDS} second timeout."
        exit_code = None
    wall_clock = time.monotonic() - started_monotonic
    ended_at = iso_now()

    reported = last_json_object(stdout) or {}
    checks_total = len(suite_tasks())
    passed = exit_code == 0 and reported.get("outcome") == "pass"
    correctness: dict = {
        "outcome": "pass" if passed else "fail",
        "checks_total": checks_total,
        "failed_check_ids": list(reported.get("failed_task_ids") or []),
    }
    if passed:
        counted = reported.get("evaluated_task_count")
        correctness["checks_passed"] = counted if isinstance(counted, int) else checks_total
    else:
        # The runner stops at the first failed assertion, so the number of checks
        # that passed is genuinely unknown. Say so rather than guessing zero.
        correctness["checks_passed"] = None
        correctness["checks_passed_unavailable_reason"] = (
            "The runner aborts at the first failed assertion, so it does not report how "
            "many checks passed or which one failed. Read the process output below."
        )

    telemetry, telemetry_meta = session_telemetry(run_id)
    cost = None
    provenance = {"extraction": "deterministic", "telemetry_source": None, "session_path": None}
    if isinstance(telemetry, dict):
        candidate = telemetry.get("cost") if isinstance(telemetry.get("cost"), dict) else telemetry
        keys = ("input_tokens", "output_tokens", "total_tokens", "estimated_usd")
        if any(isinstance(candidate.get(key), (int, float)) for key in keys):
            cost = candidate
        if isinstance(telemetry.get("provenance"), dict):
            provenance = telemetry["provenance"]
        else:
            provenance = {
                "extraction": "deterministic",
                "telemetry_source": telemetry.get("telemetry_source") or "session-transcript",
                "session_path": telemetry_meta.get("session_path"),
            }

    time_block: dict = {"agent_wall_clock_seconds": round(wall_clock, 3)}
    baseline = human_baseline()
    if baseline:
        time_block["human_baseline_minutes"] = baseline["minutes"]
        time_block["human_baseline_source"] = baseline["source"]
        time_block["time_saved_minutes"] = round(baseline["minutes"] - wall_clock / 60, 2)
        if wall_clock > 0:
            time_block["speedup_factor"] = round(baseline["minutes"] * 60 / wall_clock, 1)

    record: dict = {
        "schema_version": RUN_RECORD_SCHEMA,
        "run_id": run_id,
        "suite_id": SUITE_ID,
        "arm": DEFAULT_ARM,
        "started_at": started_at,
        "ended_at": ended_at,
        "host": {
            "name": "python-deterministic-runner",
            "version": platform.python_version(),
            "model": None,
        },
        "correctness": correctness,
        "time": time_block,
        "provenance": provenance,
        # Additive to the schema: the schema records that a block is absent but not
        # why. A reader of this page needs the reason, so it is carried here.
        "unmeasured": {},
        "process": {
            "command": f"python3 {RUNNER.relative_to(ROOT)}",
            "exit_code": exit_code,
            "timed_out": timed_out,
            "timeout_seconds": RUN_TIMEOUT_SECONDS,
            "stdout": stdout,
            "stderr": stderr,
        },
    }
    if cost is not None:
        record["cost"] = cost
    else:
        # The plan's account of why there is no cost comes first; the extractor's
        # complaint only wins when a session was actually configured for this run.
        extractor_reason = telemetry_meta.get("reason")
        configured = bool(os.environ.get("ASCENT_EVAL_SESSION", "").strip())
        record["unmeasured"]["cost"] = (extractor_reason if configured and extractor_reason else plan_reason("cost"))
    if not baseline:
        record["unmeasured"]["human_baseline_minutes"] = plan_reason("human_baseline_minutes")
    record["unmeasured"]["golden_comparison"] = plan_reason("golden_comparison")
    record["unmeasured"]["behavior"] = plan_reason("behavior")

    write_run_record(record)
    return record


# ---------------------------------------------------------------------- server


class WorkbenchHandler(SimpleHTTPRequestHandler):
    server_version = "AscentEvalWorkbench/2.0"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(DOCS), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        sys.stderr.write("%s %s\n" % (self.address_string(), format % args))

    def send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = (json.dumps(payload, indent=2, default=str) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def refuse(self, suite: str) -> None:
        self.send_json(
            {
                "error": "Unknown suite.",
                "detail": f"This workbench exposes only the allowlisted suite '{SUITE_ID}'. Requested: '{suite}'.",
            },
            HTTPStatus.NOT_FOUND,
        )

    def limit_param(self, query: dict) -> Optional[int]:
        raw = (query.get("limit") or [""])[0]
        if not re.fullmatch(r"\d{1,3}", raw or ""):
            return None
        return max(1, min(int(raw), 100))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if not path.startswith("/api/"):
            super().do_GET()
            return
        parts = [segment for segment in path.split("/") if segment]
        try:
            if path == "/api/suites":  # retained alias
                self.send_json({"suites": [suite_payload()]})
                return
            if len(parts) == 3 and parts[1] in {"suite", "runs", "summary", "results", "paste"}:
                _, endpoint, suite = parts
                if suite != SUITE_ID:
                    self.refuse(suite)
                    return
                if endpoint == "suite":
                    self.send_json(suite_payload())
                elif endpoint == "runs":
                    self.send_json(load_runs(self.limit_param(query)))
                elif endpoint == "summary":
                    self.send_json(summary_payload())
                elif endpoint == "paste":
                    self.send_json(paste_block())
                else:
                    history = load_runs(1)
                    self.send_json({"run": history["runs"][0] if history["runs"] else None})
                return
        except Exception as error:  # local tool: report the fault, do not fake data
            self.send_json({"error": type(error).__name__, "detail": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_json({"error": "Unknown endpoint.", "detail": path}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parts = [segment for segment in urlparse(self.path).path.split("/") if segment]
        if len(parts) != 3 or parts[0] != "api" or parts[1] != "run":
            self.send_json({"error": "Unknown endpoint.", "detail": self.path}, HTTPStatus.NOT_FOUND)
            return
        if parts[2] != SUITE_ID:
            self.refuse(parts[2])
            return
        if not RUN_LOCK.acquire(blocking=False):
            self.send_json({"error": f"The {SUITE_ID} suite is already running."}, HTTPStatus.CONFLICT)
            return
        try:
            self.send_json({"run": run_suite()})
        except Exception as error:
            self.send_json({"error": type(error).__name__, "detail": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
        finally:
            RUN_LOCK.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local skill-evaluation workbench.")
    parser.add_argument("--port", type=int, default=8765, help="localhost port (default: 8765)")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), WorkbenchHandler)
    print(f"Evaluation workbench: http://127.0.0.1:{args.port}/evals-workbench.html")
    print(f"Allowlisted suite: {SUITE_ID}. Cost and time telemetry: {AGGREGATE_COMMAND}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping evaluation workbench.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

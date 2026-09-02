#!/usr/bin/env python3
"""Hermetic, repeated regression suite for the project-context skills.

What this proves
----------------
1. **Did it do the job right?** A registry of named code checks over the
   artifacts the shipped skill scripts produce, graded per task contract in
   ``cases/tasks.jsonl``. Every check is recorded with its own id and assertion
   class, and a check that never executed counts as a failure rather than
   quietly vanishing from the denominator.

2. **Is the output reproducible?** The whole pipeline runs ``--runs`` times over
   the same pinned fixture in a fresh temporary workspace each time, and the
   graded artifacts are hashed and compared byte for byte. A determinism suite
   that runs once proves nothing.

What this does not prove
------------------------
No model runs here. The harness invokes the skill scripts directly, so there is
no session log, no tokens, no dollars, no agent elapsed time and no meaningful
"without the skills" arm. Those fields carry an explicit absence marker in the
run record and a named gap in ``eval-plan.json``. They are never backfilled with
a zero.

Residual non-determinism is named, not smoothed over
----------------------------------------------------
The target scripts stamp ``datetime.now(timezone.utc)`` into their artifacts and
expose no injectable clock, so the raw artifacts differ between runs. The suite
reports both digests: the raw one (expected to differ, and it says so) and the
one taken after a short, enumerated normalisation ruleset. Any cross-run
difference that the declared rules do not explain fails the suite and is
reported with its file and line. That is the difference between naming residual
non-determinism and hiding it.

Usage
-----
    python3 evals/context-skills/run_deterministic.py
    python3 evals/context-skills/run_deterministic.py --runs 7
    python3 evals/context-skills/run_deterministic.py --results-dir /tmp/out
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence, Tuple


EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[1]

SUITE_ID = "context-skills"
ARM = "with-skills"
RUN_RECORD_SCHEMA = "ascent.eval-run-record.v1"

CASE_PATH = EVAL_DIR / "cases" / "ascent-mobilize-risk-gate-1.json"
TASKS_PATH = EVAL_DIR / "cases" / "tasks.jsonl"
PLAN_PATH = EVAL_DIR / "eval-plan.json"
PROFILE_PATH = EVAL_DIR / "skill-profile.json"
BASELINE_PATH = EVAL_DIR / "baseline" / "human-baseline.json"
RECORD_CONTRACT_PATH = EVAL_DIR / "schemas" / "run-record.contract.json"

SKILLS_ROOT = ROOT / "plugins" / "ascent" / "skills"
DISCOVERY = SKILLS_ROOT / "investigate-project" / "scripts" / "project_context.py"
RANK = SKILLS_ROOT / "investigate-project" / "scripts" / "rank_context.py"
PERSIST = SKILLS_ROOT / "investigate-project" / "scripts" / "persist_context.py"
CACHE = SKILLS_ROOT / "investigate-project" / "scripts" / "cache_context.py"

TARGET_SCRIPTS = {
    "project_context.py": DISCOVERY,
    "rank_context.py": RANK,
    "persist_context.py": PERSIST,
    "cache_context.py": CACHE,
}

# Main superseded `.codex/project-context/` in commit 3f40c53. The manifest,
# brief and persisted hierarchy now live here, under the opportunity root.
CONTEXT_SUBPATH = ("workspace", ".system", "project-context")


# --------------------------------------------------------------------- hermeticity

# Injected on PYTHONPATH so every subprocess the harness starts refuses to open a
# socket. This is enforcement rather than an assertion: a target script that grew
# a network call would fail the run instead of silently reaching the internet and
# making the suite depend on someone's connectivity.
SITECUSTOMIZE = '''"""Injected by the context-skills eval harness. Any network use fails loudly."""

import socket


class OfflineViolation(RuntimeError):
    pass


_MESSAGE = "network access is blocked inside the context-skills eval harness"
_real_socket = socket.socket


class _BlockedSocket(_real_socket):
    def __init__(self, *args, **kwargs):
        raise OfflineViolation(_MESSAGE)


def _blocked(*args, **kwargs):
    raise OfflineViolation(_MESSAGE)


socket.socket = _BlockedSocket
socket.create_connection = _blocked
socket.socketpair = _blocked
socket.getaddrinfo = _blocked
socket.gethostbyname = _blocked
'''


def hermetic_env(home: Path, temp_root: Path, site_dir: Path, hash_seed: int) -> Dict[str, str]:
    """Build a scrubbed environment for a subprocess.

    Everything inherited from the developer's shell is dropped. ``HOME`` points at
    a throwaway directory, so a target script that read a dotfile would see an
    empty home rather than this machine's. ``PYTHONHASHSEED`` is deliberately
    *varied* across runs rather than pinned: pinning it would hide set-ordering
    non-determinism, which is exactly the class of bug this suite exists to catch.
    """
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(home),
        "TMPDIR": str(temp_root),
        "LC_ALL": "C",
        "LANG": "C",
        "TZ": "UTC",
        "PYTHONPATH": str(site_dir),
        "PYTHONHASHSEED": str(hash_seed),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONIOENCODING": "utf-8",
    }


# ------------------------------------------------------------------ normalisation

# Each rule names one source of residual non-determinism, why it exists, and what
# would close it. Nothing is normalised that is not listed here, and a cross-run
# difference these rules cannot explain fails the suite.
NORMALISATION_RULES = [
    {
        "id": "iso8601-utc-timestamp",
        "pattern": re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z"),
        "replacement": "<UTC-TIMESTAMP>",
        "cause": (
            "The target scripts stamp datetime.now(timezone.utc) into the manifest, brief, "
            "index, per-source summaries and state file. They expose no injectable clock, and "
            "this suite does not own those scripts."
        ),
        "closed_by": (
            "An optional --now argument on project_context.py and persist_context.py, matching "
            "the one cache_context.py already accepts, so the harness can pin the clock instead "
            "of normalising it after the fact."
        ),
    },
    {
        "id": "state-manifest-digest",
        "pattern": re.compile(r'("manifest_sha256":\s*")[0-9a-f]{64}(")'),
        "replacement": r"\1<MANIFEST-DIGEST>\2",
        "cause": (
            "state.json records a sha256 over manifest.json, which contains the timestamps "
            "described by iso8601-utc-timestamp, so the digest inherits their volatility."
        ),
        "closed_by": "The same injectable clock that closes iso8601-utc-timestamp.",
    },
]


def apply_rule(rule: Dict[str, Any], text: str) -> str:
    return rule["pattern"].sub(rule["replacement"], text)


def normalise(text: str) -> str:
    for rule in NORMALISATION_RULES:
        text = apply_rule(rule, text)
    return text


def explain_line(before: str, after: str) -> str:
    """Name the single declared rule that reconciles two differing raw lines."""
    for rule in NORMALISATION_RULES:
        if apply_rule(rule, before) == apply_rule(rule, after):
            return rule["id"]
    if normalise(before) == normalise(after):
        return "combined-rules"
    return "undeclared"


# ------------------------------------------------------------------------ grading

# One entry per code check. `task_id` ties it back to a contract in
# cases/tasks.jsonl; `assertion_class` is drawn from the contract vocabulary. The
# suite never hardcodes how many checks there are: totals are len() of this list.
CHECK_DEFINITIONS = [
    ("discovery-manifest-validates", "context-discovery-metadata", "schema-validation"),
    ("discovery-sources-recorded", "context-discovery-metadata", "state-verification"),
    ("discovery-measurement-recorded", "context-discovery-metadata", "state-verification"),
    ("discovery-unavailable-state-preserved", "context-discovery-metadata", "state-verification"),
    ("discovery-no-source-body-leak", "context-discovery-metadata", "forbidden-content"),
    ("retrieval-access-gap-emitted", "context-unavailable-source", "state-verification"),
    ("retrieval-no-restricted-body", "context-unavailable-source", "forbidden-content"),
    ("retrieval-no-unrecorded-source", "context-unavailable-source", "tool-call-verification"),
    ("persist-access-gap-visible", "context-unavailable-source", "state-verification"),
    ("persist-no-restricted-body", "context-unavailable-source", "forbidden-content"),
    ("retrieval-required-evidence-selected", "context-bounded-retrieval", "relevance-selection"),
    ("retrieval-forbidden-evidence-excluded", "context-bounded-retrieval", "forbidden-content"),
    ("retrieval-total-character-budget", "context-bounded-retrieval", "bounds-check"),
    ("retrieval-per-source-cap", "context-bounded-retrieval", "bounds-check"),
    ("cache-stale-rejected", "context-cache-boundary", "freshness-check"),
    ("cache-fresh-reused", "context-cache-boundary", "freshness-check"),
    ("cache-unrelated-rejected", "context-cache-boundary", "relevance-selection"),
]


class Grader:
    """Collects every check result. A check that never ran is a failure."""

    NOT_RUN = "the check did not execute; an earlier step in its phase raised"

    def __init__(self) -> None:
        self.order = [definition[0] for definition in CHECK_DEFINITIONS]
        self.results = {}  # type: Dict[str, Dict[str, Any]]
        for check_id, task_id, assertion_class in CHECK_DEFINITIONS:
            self.results[check_id] = {
                "id": check_id,
                "task_id": task_id,
                "assertion_class": assertion_class,
                "outcome": "not-run",
                "detail": self.NOT_RUN,
            }
        self.errors = []  # type: List[Dict[str, str]]

    def record(self, check_id: str, passed: bool, failure: str = "", evidence: str = "") -> None:
        """Record one check.

        `failure` is only stored when the check fails and `evidence` only when it
        passes. Keeping them apart matters: an earlier version of this harness
        wrote "sentinel found in: " next to a passing forbidden-content check,
        which reads as the exact opposite of what happened.
        """
        if check_id not in self.results:
            raise KeyError("undeclared check id: {0}".format(check_id))
        entry = self.results[check_id]
        entry["outcome"] = "pass" if passed else "fail"
        entry["detail"] = evidence if passed else (failure or "assertion did not hold")

    def phase_error(self, phase: str, error: BaseException) -> None:
        self.errors.append({"phase": phase, "error": "{0}: {1}".format(type(error).__name__, error)})

    @property
    def failed_ids(self) -> List[str]:
        return [cid for cid in self.order if self.results[cid]["outcome"] != "pass"]

    @property
    def passed_count(self) -> int:
        return sum(1 for cid in self.order if self.results[cid]["outcome"] == "pass")

    def task_rollup(self, task_ids: Sequence[str]) -> List[Dict[str, Any]]:
        rollup = []
        for task_id in task_ids:
            checks = [self.results[cid] for cid in self.order if self.results[cid]["task_id"] == task_id]
            failed = [check["id"] for check in checks if check["outcome"] != "pass"]
            rollup.append(
                {
                    "task_id": task_id,
                    "outcome": "pass" if checks and not failed else "fail",
                    "checks_total": len(checks),
                    "checks_passed": len(checks) - len(failed),
                    "failed_check_ids": failed,
                }
            )
        return rollup


# ------------------------------------------------------------------------ plumbing


class Runner:
    def __init__(self, env: Dict[str, str]) -> None:
        self.env = env
        self.calls = 0

    def __call__(self, *args: str) -> str:
        code, stdout, stderr = self.attempt(*args)
        if code:
            raise RuntimeError(
                "{0} exited {1}: {2}".format(Path(args[0]).name, code, stderr.strip())
            )
        return stdout

    def attempt(self, *args: str) -> Tuple[int, str, str]:
        self.calls += 1
        result = subprocess.run(
            [sys.executable] + list(args),
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_to_root(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise. Never raises."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def to_iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ------------------------------------------------------------------------ one run


class Trial:
    """State shared between the graded phases of a single run."""

    def __init__(self, workspace: Path, case: Dict[str, Any], runner: Runner, grader: Grader) -> None:
        self.workspace = workspace
        self.case = case
        self.run = runner
        self.grader = grader
        self.context_dir = workspace.joinpath(*CONTEXT_SUBPATH)
        self.ranked_path = workspace / "ranked.jsonl"
        self.gaps_path = workspace / "gaps.json"
        self.chunks_path = workspace / "chunks.jsonl"
        self.pack_path = workspace / "pack.json"
        self.manifest = {}  # type: Dict[str, Any]
        self.ranked = []  # type: List[Dict[str, Any]]
        self.gaps = []  # type: List[Dict[str, Any]]
        self.cache_decisions = {}  # type: Dict[str, Dict[str, Any]]

    @property
    def manifest_path(self) -> Path:
        return self.context_dir / "manifest.json"


def phase_discovery(trial: Trial) -> None:
    case, run, grader = trial.case, trial.run, trial.grader
    project = case["project"]
    workspace = str(trial.workspace)
    run(str(DISCOVERY), "init", "--root", workspace, "--name", project["name"], "--objective", project["objective"])
    run(str(DISCOVERY), "set-project", "--root", workspace, "--phase", project["phase"])
    for source in case["sources"]:
        args = [
            str(DISCOVERY), "upsert-source", "--root", workspace,
            "--id", source["id"], "--kind", source["kind"], "--label", source["label"],
            "--locator", source["locator"], "--purpose", source["purpose"],
            "--authority", source["authority"], "--priority", str(source["priority"]),
            "--freshness-hours", str(source["freshness_hours"]),
            "--access-state", source["access_state"],
        ]
        for hint in source["query_hints"]:
            args.extend(["--query-hint", hint])
        if source.get("access_reason"):
            args.extend(["--access-reason", source["access_reason"]])
        run(*args)

    metrics = case["metrics"]
    args = [
        str(DISCOVERY), "record-discovery", "--root", workspace,
        "--sources-considered", str(metrics["sources_considered"]),
        "--sources-recorded", str(metrics["sources_recorded"]),
        "--connector-calls", str(metrics["connector_calls"]),
        "--items-inspected", str(metrics["items_inspected"]),
        "--characters-inspected", str(metrics["characters_inspected"]),
    ]
    for cap in metrics["caps"]:
        args.extend(["--cap", cap])
    run(*args)
    run(str(DISCOVERY), "render-brief", "--root", workspace)

    code, _, stderr = run.attempt(str(DISCOVERY), "validate", "--root", workspace)
    grader.record(
        "discovery-manifest-validates",
        code == 0,
        "" if code == 0 else "validate exited {0}: {1}".format(code, stderr.strip()),
    )

    manifest_text = trial.manifest_path.read_text(encoding="utf-8")
    brief_text = (trial.context_dir / "brief.md").read_text(encoding="utf-8")
    trial.manifest = json.loads(manifest_text)
    recorded = dict((source["id"], source) for source in trial.manifest.get("sources", []))

    mismatches = []
    for source in case["sources"]:
        actual = recorded.get(source["id"])
        if actual is None:
            mismatches.append("{0}: not recorded".format(source["id"]))
            continue
        for field in ("kind", "label", "locator", "purpose", "authority", "priority", "freshness_hours"):
            if actual.get(field) != source[field]:
                mismatches.append(
                    "{0}.{1}: {2!r} != {3!r}".format(source["id"], field, actual.get(field), source[field])
                )
    grader.record(
        "discovery-sources-recorded",
        not mismatches,
        failure="; ".join(mismatches),
        evidence="{0} declared source(s) recorded with matching metadata".format(len(case["sources"])),
    )

    discovery_runs = trial.manifest.get("discovery_runs") or []
    if not discovery_runs:
        grader.record("discovery-measurement-recorded", False, "no discovery run was recorded")
    else:
        latest = discovery_runs[-1]
        expected_caps = dict(item.split("=", 1) for item in metrics["caps"])
        problems = [
            "{0}: {1!r} != {2!r}".format(field, latest.get(field), metrics[field])
            for field in (
                "sources_considered", "sources_recorded", "connector_calls",
                "items_inspected", "characters_inspected",
            )
            if latest.get(field) != metrics[field]
        ]
        caps = latest.get("exploration_caps") or {}
        problems.extend(
            "cap {0}: {1!r} != {2!r}".format(system, caps.get(system), int(value))
            for system, value in sorted(expected_caps.items())
            if caps.get(system) != int(value)
        )
        grader.record(
            "discovery-measurement-recorded",
            not problems,
            failure="; ".join(problems),
            evidence="bounded discovery measurement and {0} exploration cap(s) recorded".format(
                len(expected_caps)
            ),
        )

    unavailable = [source for source in case["sources"] if source["access_state"] != "available"]
    lost = [
        source["id"]
        for source in unavailable
        if (recorded.get(source["id"], {}).get("access") or {}).get("state") != source["access_state"]
    ]
    grader.record(
        "discovery-unavailable-state-preserved",
        bool(unavailable) and not lost,
        failure=(
            "the fixture declares no unavailable source, so this check has nothing to assert"
            if not unavailable
            else "access state lost for: " + ", ".join(lost)
        ),
        evidence="access state preserved for: " + ", ".join(source["id"] for source in unavailable),
    )

    sentinel = case["sentinel"]
    leaked = [
        name
        for name, text in (("manifest.json", manifest_text), ("brief.md", brief_text))
        if sentinel in text
    ]
    grader.record(
        "discovery-no-source-body-leak",
        not leaked,
        failure="sentinel found in: " + ", ".join(leaked),
        evidence="sentinel absent from manifest.json and brief.md",
    )


def phase_retrieval(trial: Trial) -> None:
    case, run, grader = trial.case, trial.run, trial.grader
    retrieval = case["retrieval"]
    trial.chunks_path.write_text(
        "".join(json.dumps(chunk, sort_keys=True) + "\n" for chunk in retrieval["chunks"]), encoding="utf-8"
    )
    run(
        str(RANK),
        "--manifest", str(trial.manifest_path),
        "--chunks", str(trial.chunks_path),
        "--task", retrieval["task"],
        "--output", str(trial.ranked_path),
        "--top-n", "10",
        "--max-per-source", str(retrieval["max_per_source"]),
        "--gaps-output", str(trial.gaps_path),
    )
    ranked_text = trial.ranked_path.read_text(encoding="utf-8")
    trial.ranked = read_jsonl(trial.ranked_path)
    trial.gaps = json.loads(trial.gaps_path.read_text(encoding="utf-8"))
    selected = [item["chunk_id"] for item in trial.ranked]

    unavailable_ids = set(
        source["id"] for source in case["sources"] if source["access_state"] != "available"
    )
    gap_ids = set(gap.get("source_id") for gap in trial.gaps)
    missing_gaps = sorted(unavailable_ids - gap_ids)
    grader.record(
        "retrieval-access-gap-emitted",
        bool(unavailable_ids) and not missing_gaps,
        failure=(
            "the fixture declares no unavailable source, so this check has nothing to assert"
            if not unavailable_ids
            else "no access gap emitted for: " + ", ".join(missing_gaps)
        ),
        evidence="access gap emitted for: " + ", ".join(sorted(unavailable_ids)),
    )

    sentinel = case["sentinel"]
    gaps_text = trial.gaps_path.read_text(encoding="utf-8")
    leaked = [name for name, text in (("ranked.jsonl", ranked_text), ("gaps.json", gaps_text)) if sentinel in text]
    grader.record(
        "retrieval-no-restricted-body",
        not leaked,
        failure="sentinel found in: " + ", ".join(leaked),
        evidence="sentinel absent from ranked.jsonl and gaps.json",
    )

    recorded_ids = set(source["id"] for source in trial.manifest.get("sources", []))
    available_ids = recorded_ids - unavailable_ids
    widened = sorted(set(item.get("source_id") for item in trial.ranked) - available_ids)
    grader.record(
        "retrieval-no-unrecorded-source",
        not widened,
        failure="evidence drawn from outside the available recorded set: "
        + ", ".join(str(item) for item in widened),
        evidence="evidence drawn only from: " + ", ".join(sorted(available_ids)),
    )

    required = list(retrieval["required_chunk_ids"])
    absent = [chunk_id for chunk_id in required if chunk_id not in selected]
    grader.record(
        "retrieval-required-evidence-selected",
        not absent,
        failure="required evidence not selected: " + ", ".join(absent),
        evidence="required evidence selected: " + ", ".join(required),
    )

    forbidden = list(retrieval["forbidden_chunk_ids"])
    present = [chunk_id for chunk_id in forbidden if chunk_id in selected]
    grader.record(
        "retrieval-forbidden-evidence-excluded",
        bool(forbidden) and not present,
        failure=(
            "the fixture declares no forbidden chunk, so this check has nothing to assert"
            if not forbidden
            else "forbidden evidence selected: " + ", ".join(present)
        ),
        evidence="forbidden evidence excluded: " + ", ".join(forbidden),
    )

    total_chars = sum(len(item["text"]) for item in trial.ranked)
    budget = retrieval["max_total_chars"]
    budget_reading = "{0} characters selected against a {1} character budget".format(total_chars, budget)
    grader.record(
        "retrieval-total-character-budget",
        total_chars <= budget,
        failure=budget_reading,
        evidence=budget_reading,
    )

    per_source = {}  # type: Dict[str, int]
    for item in trial.ranked:
        per_source[item["source_id"]] = per_source.get(item["source_id"], 0) + 1
    cap = retrieval["max_per_source"]
    over = ["{0}={1}".format(sid, count) for sid, count in sorted(per_source.items()) if count > cap]
    selection = ", ".join("{0}={1}".format(sid, count) for sid, count in sorted(per_source.items()))
    grader.record(
        "retrieval-per-source-cap",
        not over,
        failure="over the per-source cap of {0}: {1}".format(cap, ", ".join(over)),
        evidence="per-source selection against a cap of {0}: {1}".format(cap, selection),
    )


def phase_persist(trial: Trial) -> None:
    case, run, grader = trial.case, trial.run, trial.grader
    pack = {
        "task": case["retrieval"]["task"],
        "overview": "Bounded Mobilize evidence.",
        "access_gaps": trial.gaps,
        "sources": [
            {"source_id": item["source_id"], "summary": item["title"], "excerpts": [item]}
            for item in trial.ranked
        ],
    }
    trial.pack_path.write_text(json.dumps(pack, sort_keys=True), encoding="utf-8")
    run(
        str(PERSIST),
        "--manifest", str(trial.manifest_path),
        "--pack", str(trial.pack_path),
        "--context-dir", str(trial.context_dir),
    )
    index_text = (trial.context_dir / "index.md").read_text(encoding="utf-8")
    grader.record(
        "persist-access-gap-visible",
        "## Access Gaps" in index_text,
        failure="the persisted index has no Access Gaps section",
        evidence="the persisted index carries an Access Gaps section",
    )

    sentinel = case["sentinel"]
    leaked = sorted(
        path.relative_to(trial.context_dir).as_posix()
        for path in trial.context_dir.rglob("*")
        if path.is_file() and sentinel in path.read_text(encoding="utf-8", errors="replace")
    )
    grader.record(
        "persist-no-restricted-body",
        not leaked,
        failure="sentinel found in: " + ", ".join(leaked),
        evidence="sentinel absent from every file under the persisted context directory",
    )


def phase_cache(trial: Trial) -> None:
    case, run, grader = trial.case, trial.run, trial.grader
    spec = case["cache"]
    source_id = spec["source_id"]
    state = json.loads((trial.context_dir / "state.json").read_text(encoding="utf-8"))
    retrieved = (state.get("sources") or {}).get(source_id, {}).get("last_retrieved_at")
    if not retrieved:
        raise RuntimeError("no recorded retrieval timestamp for cache source {0!r}".format(source_id))

    # The clock is pinned against the recorded retrieval timestamp rather than read
    # from the machine, so age_hours is an exact number in every run.
    fresh_now = retrieved
    stale_now = to_iso(parse_iso(retrieved) + timedelta(hours=spec["stale_offset_hours"]))

    def decide(task: str, now: str) -> Dict[str, Any]:
        return json.loads(
            run(
                str(CACHE),
                "--manifest", str(trial.manifest_path),
                "--context-dir", str(trial.context_dir),
                "--source-id", source_id,
                "--task", task,
                "--now", now,
            )
        )

    stale = decide(spec["relevant_task"], stale_now)
    fresh = decide(spec["relevant_task"], fresh_now)
    unrelated = decide(spec["unrelated_task"], fresh_now)
    trial.cache_decisions = {"stale": stale, "fresh": fresh, "unrelated": unrelated}

    def reading(decision):
        return "reuse={0!r} age_hours={1!r} reason={2!r}".format(
            decision.get("reuse"), decision.get("age_hours"), decision.get("reason")
        )

    grader.record("cache-stale-rejected", stale.get("reuse") is False, failure=reading(stale), evidence=reading(stale))
    grader.record("cache-fresh-reused", fresh.get("reuse") is True, failure=reading(fresh), evidence=reading(fresh))
    grader.record(
        "cache-unrelated-rejected",
        unrelated.get("reuse") is False,
        failure=reading(unrelated),
        evidence=reading(unrelated),
    )


PHASES = [
    ("discovery", phase_discovery),
    ("retrieval", phase_retrieval),
    ("persist", phase_persist),
    ("cache", phase_cache),
]  # type: List[Tuple[str, Callable[[Trial], None]]]


PATH_SUBSTITUTION_KEY = "__path_substitutions__"


def collect_bundle(trial: Trial, placeholders: Sequence[Tuple[str, str]]) -> Dict[str, str]:
    """Every graded artifact, keyed by a stable relative name.

    The whole context directory is walked rather than a named list of files, so a
    new artifact is picked up automatically and a renamed one does not silently
    drop out of the comparison.
    """
    bundle = {}  # type: Dict[str, str]
    for path in sorted(trial.context_dir.rglob("*")):
        if path.is_file():
            key = "context/" + path.relative_to(trial.context_dir).as_posix()
            bundle[key] = path.read_text(encoding="utf-8", errors="replace")
    if trial.ranked_path.exists():
        bundle["retrieval/ranked.jsonl"] = trial.ranked_path.read_text(encoding="utf-8")
    if trial.gaps_path.exists():
        bundle["retrieval/gaps.json"] = trial.gaps_path.read_text(encoding="utf-8")
    for name in sorted(trial.cache_decisions):
        bundle["cache/{0}.json".format(name)] = (
            json.dumps(trial.cache_decisions[name], indent=2, sort_keys=True) + "\n"
        )

    substitutions = 0
    for literal, token in placeholders:
        if not literal:
            continue
        for key in list(bundle):
            text = bundle[key]
            if literal in text:
                substitutions += text.count(literal)
                bundle[key] = text.replace(literal, token)
    bundle[PATH_SUBSTITUTION_KEY] = str(substitutions)
    return bundle


def bundle_digest(bundle: Dict[str, str]) -> str:
    lines = [
        "{0}\t{1}".format(key, sha256_text(bundle[key]))
        for key in sorted(bundle)
        if key != PATH_SUBSTITUTION_KEY
    ]
    return sha256_text("\n".join(lines))


def execute_trial(case: Dict[str, Any], hash_seed: int) -> Dict[str, Any]:
    grader = Grader()
    started = time.monotonic()
    temp_root = Path(tempfile.mkdtemp(prefix="ascent-context-eval-"))
    runner = None
    try:
        workspace = temp_root / "opportunity"
        home = temp_root / "home"
        site_dir = temp_root / "site"
        for directory in (workspace, home, site_dir):
            directory.mkdir(parents=True)
        (site_dir / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")

        env = hermetic_env(home, temp_root, site_dir, hash_seed)
        runner = Runner(env)
        trial = Trial(workspace, case, runner, grader)
        for name, phase in PHASES:
            try:
                phase(trial)
            except Exception as error:  # a phase failure is data, not a crash
                grader.phase_error(name, error)
                break

        placeholders = [
            (str(workspace.resolve()), "<WORKSPACE>"),
            (str(workspace), "<WORKSPACE>"),
            (str(temp_root.resolve()), "<TEMP-ROOT>"),
            (str(temp_root), "<TEMP-ROOT>"),
            (str(ROOT), "<REPO-ROOT>"),
        ]
        bundle = collect_bundle(trial, placeholders)
    finally:
        shutil.rmtree(str(temp_root), ignore_errors=True)

    return {
        "hash_seed": hash_seed,
        "grader": grader,
        "bundle": bundle,
        "subprocess_calls": runner.calls if runner else 0,
        "seconds": round(time.monotonic() - started, 3),
    }


# --------------------------------------------------------------- cross-run compare


def compare_trials(trials: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Hash the graded artifacts of every run and account for every difference."""
    raw_digests = [bundle_digest(trial["bundle"]) for trial in trials]
    canonical_bundles = [
        dict((key, normalise(value)) for key, value in trial["bundle"].items()) for trial in trials
    ]
    canonical_digests = [bundle_digest(bundle) for bundle in canonical_bundles]

    explained = dict((rule["id"], 0) for rule in NORMALISATION_RULES)
    explained["combined-rules"] = 0
    undeclared = []  # type: List[Dict[str, Any]]

    reference = trials[0]["bundle"]
    reference_canonical = canonical_bundles[0]
    for index in range(1, len(trials)):
        other = trials[index]["bundle"]
        other_canonical = canonical_bundles[index]
        for key in sorted(set(reference) ^ set(other)):
            undeclared.append({"path": key, "kind": "file-present-in-only-one-run", "runs": [0, index]})
        for key in sorted(set(reference) & set(other)):
            if reference[key] == other[key]:
                continue
            if reference_canonical[key] != other_canonical[key]:
                left = reference_canonical[key].splitlines()
                right = other_canonical[key].splitlines()
                sample = {"expected": "<line count differs>", "observed": "<line count differs>"}
                for a, b in zip(left, right):
                    if a != b:
                        sample = {"expected": a, "observed": b}
                        break
                undeclared.append(
                    {
                        "path": key,
                        "kind": "differs-after-declared-normalisation",
                        "runs": [0, index],
                        "sample": sample,
                    }
                )
                continue
            for a, b in zip(reference[key].splitlines(), other[key].splitlines()):
                if a == b:
                    continue
                attribution = explain_line(a, b)
                explained[attribution] = explained.get(attribution, 0) + 1

    declared = [
        {
            "id": rule["id"],
            "differing_lines_explained": explained.get(rule["id"], 0),
            "cause": rule["cause"],
            "closed_by": rule["closed_by"],
        }
        for rule in NORMALISATION_RULES
    ]
    if explained.get("combined-rules"):
        declared.append(
            {
                "id": "combined-rules",
                "differing_lines_explained": explained["combined-rules"],
                "cause": "Lines that only reconcile once more than one declared rule is applied.",
                "closed_by": "Whatever closes the contributing rules.",
            }
        )

    identical_raw = len(set(raw_digests)) == 1
    identical_canonical = len(set(canonical_digests)) == 1 and not undeclared
    return {
        "runs_compared": len(trials),
        "hash_seeds_used": [trial["hash_seed"] for trial in trials],
        "graded_artifact_count": len([key for key in reference if key != PATH_SUBSTITUTION_KEY]),
        "path_substitutions_made": sum(int(trial["bundle"][PATH_SUBSTITUTION_KEY]) for trial in trials),
        "identical_before_normalisation": identical_raw,
        "identical_after_declared_normalisation": identical_canonical,
        "raw_artifact_sha256": raw_digests,
        "canonical_artifact_sha256": canonical_digests,
        "declared_volatility": declared,
        "undeclared_variation": undeclared,
        "verdict": "reproducible-modulo-declared-volatility" if identical_canonical else "not-reproducible",
        "method": (
            "Every run builds a fresh temporary workspace from the same pinned fixture, and every "
            "graded artifact is hashed. Runs are compared against run 1 both raw and after the "
            "declared normalisation rules. A difference the declared rules cannot explain fails "
            "the suite and is listed in undeclared_variation."
        ),
        "single_run_caveat": (
            "A single run cannot support a reproducibility claim: with runs_compared 1 there is "
            "nothing to compare and identical_* are trivially true."
        ),
    }


# ------------------------------------------------------------------- run records


def validate_record(record: Dict[str, Any], contract: Dict[str, Any]) -> List[str]:
    problems = []
    if record.get("schema_version") != contract["schema_version"]:
        problems.append("schema_version is {0!r}".format(record.get("schema_version")))
    for key in contract["required_keys"]:
        if key not in record:
            problems.append("missing top-level key {0!r}".format(key))
    for block in sorted(contract["required_block_keys"]):
        section = record.get(block)
        if not isinstance(section, dict):
            problems.append("block {0!r} is not an object".format(block))
            continue
        problems.extend(
            "missing {0}.{1}".format(block, key)
            for key in contract["required_block_keys"][block]
            if key not in section
        )
    if record.get("arm") not in contract["arm_values"]:
        problems.append("arm {0!r} is not one of {1}".format(record.get("arm"), contract["arm_values"]))
    correctness = record.get("correctness") or {}
    if correctness.get("outcome") not in contract["correctness_outcome_values"]:
        problems.append("correctness.outcome {0!r} is not permitted".format(correctness.get("outcome")))
    provenance = record.get("provenance") or {}
    if provenance.get("extraction") not in contract["provenance_extraction_values"]:
        problems.append("provenance.extraction {0!r} is not permitted".format(provenance.get("extraction")))
    for dotted in contract["omit_unless_recorded"]:
        block, key = dotted.split(".", 1)
        section = record.get(block) or {}
        if key in section and section[key] is None:
            problems.append("{0} is present as null; omit it instead".format(dotted))
    return problems


def next_run_index(results_runs: Path, stamp: str) -> int:
    """Match the run-id scheme the workbench already uses, and never clobber."""
    if not results_runs.is_dir():
        return 1
    return len(list(results_runs.glob("{0}-{1}-*.json".format(SUITE_ID, stamp)))) + 1


def build_record(
    run_id,
    trial,
    determinism,
    task_ids,
    profile,
    baseline,
    started_at,
    ended_at,
    sibling_run_ids,
    case_path,
):
    grader = trial["grader"]  # type: Grader
    rollup = grader.task_rollup(task_ids)
    failed_tasks = [item["task_id"] for item in rollup if item["outcome"] != "pass"]
    outcome = "pass" if not grader.failed_ids and not grader.errors else "fail"

    not_applicable = "not-applicable"
    not_observable = "not-observable"

    record = {
        "schema_version": RUN_RECORD_SCHEMA,
        "run_id": run_id,
        "suite_id": SUITE_ID,
        "arm": ARM,
        "started_at": started_at,
        "ended_at": ended_at,
        "host": {
            "name": "python-script-harness",
            "version": "{0} {1}".format(platform.python_implementation(), platform.python_version()),
            "model": not_applicable,
            "model_note": (
                "No model runs in this suite. The harness invokes the shipped skill scripts "
                "directly, so there is nothing to record a model name for."
            ),
        },
        "correctness": {
            "outcome": outcome,
            "checks_total": len(grader.order),
            "checks_passed": grader.passed_count,
            "failed_check_ids": grader.failed_ids,
            "checks": [grader.results[cid] for cid in grader.order],
            "evaluated_task_count": len(rollup),
            "outcome_pass_rate": (
                round((len(rollup) - len(failed_tasks)) / float(len(rollup)), 4) if rollup else None
            ),
            "failed_task_ids": failed_tasks,
            "tasks": rollup,
            "harness_errors": grader.errors,
        },
        "cost": {
            "input_tokens": not_applicable,
            "output_tokens": not_applicable,
            "cache_read_tokens": not_applicable,
            "cache_creation_tokens": not_applicable,
            "total_tokens": not_applicable,
            "estimated_usd": None,
            "turns": not_applicable,
            "tool_calls": not_applicable,
            "note": (
                "Structurally absent, not unmeasured. This suite runs local Python scripts, so "
                "there is no model, no session log and no token accounting to parse. estimated_usd "
                "is null because no rate applies to a run with no model, and a 0.0 there would be "
                "a false cost claim rather than a missing one. See the no-cost-data gap in "
                "eval-plan.json."
            ),
            "harness_subprocess_calls": trial["subprocess_calls"],
            "harness_subprocess_calls_note": (
                "Count of skill-script invocations the harness made. This is not an agentic "
                "tool-call count and must not be presented as one."
            ),
        },
        "time": {
            "agent_wall_clock_seconds": not_applicable,
            "agent_wall_clock_note": (
                "There is no agent in this suite, so there is no agent elapsed time. The harness "
                "runtime below is machine speed, not a saving, and must never be substituted for "
                "agent wall clock."
            ),
            "harness_wall_clock_seconds": trial["seconds"],
        },
        "behavior": {
            "skills_invoked": not_observable,
            "skills_expected": list(profile.get("expected_skill_invocations") or []),
            "missing_skill_invocations": not_observable,
            "clarifying_questions_asked": not_observable,
            "clarifying_questions_required": list(profile.get("required_clarifying_questions") or []),
            "note": (
                "The harness calls the skill scripts itself, so nothing here shows that a model "
                "would have chosen these skills or asked these questions. Recorded so an agentic "
                "arm can assert it later. See the behavior-not-observable gap in eval-plan.json."
            ),
        },
        "determinism": dict(determinism, sibling_run_ids=list(sibling_run_ids)),
        "hermeticity": {
            "workspace": "fresh temporary directory per run, deleted afterwards",
            "home_redirected": True,
            "environment": (
                "The inherited shell environment is discarded. Only PATH, HOME, TMPDIR, LC_ALL, "
                "LANG, TZ and PYTHON* are set, so no developer setting reaches a target script."
            ),
            "network": {
                "policy": "blocked",
                "enforcement": (
                    "A sitecustomize.py on PYTHONPATH raises on socket construction, "
                    "create_connection, socketpair, getaddrinfo and gethostbyname in every "
                    "subprocess, so a network call fails the run rather than succeeding quietly."
                ),
            },
            "clock": {
                "pinned_where_the_interface_allows": True,
                "note": (
                    "cache_context.py accepts --now, so the cache decisions are taken against the "
                    "recorded retrieval timestamp plus a fixed offset from the fixture, not the "
                    "machine clock. project_context.py and persist_context.py accept no clock "
                    "argument, so their timestamps stay volatile and are declared in "
                    "determinism.declared_volatility."
                ),
            },
            "hash_seed": (
                "PYTHONHASHSEED is varied across runs rather than pinned, so set-ordering "
                "non-determinism would surface instead of being masked."
            ),
            "depends_on_repo_checkout": True,
            "depends_on_repo_checkout_note": (
                "The suite executes the skill scripts from the checkout it ships inside. That is "
                "inherent to testing the library and is not a dependency on any particular "
                "machine: no absolute developer path, home directory or clock reading reaches the "
                "graded artifacts."
            ),
        },
        "provenance": {
            "telemetry_source": not_applicable,
            "telemetry_source_note": (
                "No session log exists for a script-driven run, so no telemetry was extracted."
            ),
            "session_path": None,
            "extraction": "deterministic",
            "case_fixture": relative_to_root(case_path),
            "case_fixture_sha256": sha256_file(case_path),
            "harness_sha256": sha256_file(Path(__file__).resolve()),
            "target_script_sha256": dict(
                (name, sha256_file(path)) for name, path in sorted(TARGET_SCRIPTS.items())
            ),
        },
    }

    if baseline.get("recorded") is True and isinstance(baseline.get("minutes"), (int, float)):
        record["time"]["human_baseline_minutes"] = baseline["minutes"]
        record["time"]["human_baseline_source"] = (
            baseline.get("source") or baseline.get("method") or "unknown"
        )
        record["time"]["time_saved_note"] = (
            "A human baseline is recorded, but time_saved_minutes and speedup_factor stay omitted: "
            "there is no agent elapsed time to subtract it from."
        )
    else:
        record["time"]["human_baseline_status"] = "not-recorded"
        record["time"]["human_baseline_note"] = (
            "No human has been timed assembling this evidence pack. human_baseline_minutes, "
            "time_saved_minutes and speedup_factor are omitted rather than zeroed. See the "
            "no-human-baseline gap in eval-plan.json."
        )
    return record


# ------------------------------------------------------------------------- output


def paste_ready_block(record: Dict[str, Any], determinism: Dict[str, Any]) -> str:
    correctness = record["correctness"]
    return "\n".join(
        [
            "Deliverable: local project-context projection (manifest, brief, ranked evidence pack)",
            "Suite: {0}   Arm: {1}   Runs: {2}".format(SUITE_ID, ARM, determinism["runs_compared"]),
            "Correctness: {0} - {1}/{2} checks across {3} task contracts".format(
                correctness["outcome"],
                correctness["checks_passed"],
                correctness["checks_total"],
                correctness["evaluated_task_count"],
            ),
            "Reproducibility: {0} - graded artifacts identical across {1} run(s) after {2} declared "
            "volatility rule(s); {3} unexplained difference(s)".format(
                determinism["verdict"],
                determinism["runs_compared"],
                len(determinism["declared_volatility"]),
                len(determinism["undeclared_variation"]),
            ),
            "Tokens: not-applicable (no model in this suite)",
            "Estimated cost: not-applicable (no model in this suite)",
            "Agent time: not-applicable (no model in this suite)",
            "Human baseline: {0}".format(record["time"].get("human_baseline_minutes", "not recorded")),
            "Time saved: unknown (no agent time and no human baseline)",
            "Cost consistency: unknown (no tokens measured; thresholds provisional)",
        ]
    )


def main() -> int:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(
        description="Hermetic, repeated regression suite for the project-context skills.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=None,
        help="Whole-suite repeats. Defaults to runs_per_arm in eval-plan.json.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=EVAL_DIR / "results",
        help="Where run records are written. Git-ignored by default.",
    )
    parser.add_argument(
        "--case",
        type=Path,
        default=CASE_PATH,
        help="Case fixture to grade. Defaults to the committed Mobilize Risk Gate 1 fixture.",
    )
    parser.add_argument("--quiet", action="store_true", help="Emit the JSON summary only.")
    args = parser.parse_args()

    runs = args.runs if args.runs is not None else int(plan.get("runs_per_arm") or 1)
    if runs < 1:
        parser.error("--runs must be at least 1")

    case_path = args.case
    case = json.loads(case_path.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8")) if BASELINE_PATH.exists() else {}
    contract = json.loads(RECORD_CONTRACT_PATH.read_text(encoding="utf-8"))
    task_ids = [
        json.loads(line)["id"]
        for line in TASKS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    declared = set(definition[1] for definition in CHECK_DEFINITIONS)
    unknown_tasks = sorted(declared - set(task_ids))
    uncovered_tasks = sorted(set(task_ids) - declared)
    if unknown_tasks or uncovered_tasks:
        sys.stderr.write(
            "the check registry and cases/tasks.jsonl disagree: checks naming unknown task ids "
            "{0}, task contracts with no check {1}\n".format(unknown_tasks, uncovered_tasks)
        )
        return 2

    started_at = utc_now_iso()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trials = [execute_trial(case, hash_seed=index) for index in range(runs)]
    ended_at = utc_now_iso()

    determinism = compare_trials(trials)

    runs_dir = args.results_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    first_index = next_run_index(runs_dir, stamp)
    run_ids = ["{0}-{1}-{2:02d}".format(SUITE_ID, stamp, first_index + offset) for offset in range(runs)]

    records = []
    validation_problems = []  # type: List[str]
    written = []  # type: List[str]
    for offset, trial in enumerate(trials):
        run_id = run_ids[offset]
        record = build_record(
            run_id=run_id,
            trial=trial,
            determinism=determinism,
            task_ids=task_ids,
            profile=profile,
            baseline=baseline,
            started_at=started_at,
            ended_at=ended_at,
            sibling_run_ids=[other for other in run_ids if other != run_id],
            case_path=case_path,
        )
        validation_problems.extend(
            "{0}: {1}".format(run_id, problem) for problem in validate_record(record, contract)
        )
        target = runs_dir / "{0}.json".format(run_id)
        target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(target))
        records.append(record)

    all_pass = all(record["correctness"]["outcome"] == "pass" for record in records)
    reproducible = determinism["identical_after_declared_normalisation"]
    outcome = "pass" if all_pass and reproducible and not validation_problems else "fail"

    first = records[0]
    summary = {
        "suite": SUITE_ID,
        "arm": ARM,
        "outcome": outcome,
        # Legacy keys, kept so the existing workbench keeps reading this runner.
        # They describe task contracts, not the finer-grained check registry.
        "evaluated_task_count": first["correctness"]["evaluated_task_count"],
        "outcome_pass_rate": first["correctness"]["outcome_pass_rate"],
        "failed_task_ids": sorted(
            set(tid for record in records for tid in record["correctness"]["failed_task_ids"])
        ),
        "duration_ms": round(sum(trial["seconds"] for trial in trials) * 1000),
        "runs": runs,
        "checks_total": first["correctness"]["checks_total"],
        "checks_passed_min": min(record["correctness"]["checks_passed"] for record in records),
        "failed_check_ids": sorted(
            set(cid for record in records for cid in record["correctness"]["failed_check_ids"])
        ),
        "determinism": {
            "verdict": determinism["verdict"],
            "runs_compared": determinism["runs_compared"],
            "identical_before_normalisation": determinism["identical_before_normalisation"],
            "identical_after_declared_normalisation": determinism["identical_after_declared_normalisation"],
            "canonical_artifact_sha256": determinism["canonical_artifact_sha256"][0],
            "graded_artifact_count": determinism["graded_artifact_count"],
            "declared_volatility_ids": [item["id"] for item in determinism["declared_volatility"]],
            "undeclared_variation": determinism["undeclared_variation"],
        },
        "run_record_schema": RUN_RECORD_SCHEMA,
        "run_records": written,
        "run_record_validation_problems": validation_problems,
        "unmeasured": {
            "cost": "not-applicable: no model, so no session log and no tokens",
            "agent_time": "not-applicable: no model, so no agent elapsed time",
            "human_baseline": "not-recorded",
            "baseline_no_skills_arm": (
                "not-applicable: there is no no-skills version of a shell script"
            ),
        },
    }

    if not args.quiet:
        sys.stderr.write(paste_ready_block(first, determinism) + "\n")
        if validation_problems:
            sys.stderr.write(
                "run record contract violations:\n  " + "\n  ".join(validation_problems) + "\n"
            )
        for record in records:
            for error in record["correctness"]["harness_errors"]:
                sys.stderr.write(
                    "harness error in {0} ({1}): {2}\n".format(
                        record["run_id"], error["phase"], error["error"]
                    )
                )
            for check in record["correctness"]["checks"]:
                if check["outcome"] != "pass":
                    sys.stderr.write(
                        "failed check {0} [{1}] in {2}: {3}\n".format(
                            check["id"], check["assertion_class"], record["run_id"], check["detail"]
                        )
                    )
        for failure in determinism["undeclared_variation"]:
            sys.stderr.write("undeclared non-determinism: {0}\n".format(json.dumps(failure)))

    print(json.dumps(summary, ensure_ascii=False))
    return 0 if outcome == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

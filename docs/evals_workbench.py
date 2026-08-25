#!/usr/bin/env python3
"""Serve the local skill-evaluation workbench.

    python3 docs/evals_workbench.py --port 8765
    # then open http://127.0.0.1:8765/evals-workbench.html

Calvin described this surface on 2026-08-24: "something like this, right? Where
it's just like an easy visualization, an easy way to like kick off a run and ...
allows you to understand the difference between those runs and what they
outputted ... you can point it towards a specific test run, and we can do, you
know, do it over and over and over, and you can choose how many runs you want."

So the run endpoint takes a **count**. One run cannot show a spread, and the
spread is the product claim.

Execution boundary
------------------
Unchanged in substance from the first version, and worth restating because the
page can start a subprocess:

* **Suites are discovered, then allowlisted.** A suite is a directory under
  ``evals/`` holding an ``eval-plan.json``. The browser may name a suite only
  from that discovered set, and its id must match ``SUITE_ID_PATTERN``. Nothing
  else in a request reaches the filesystem.
* **The browser supplies no command, model, path, fixture or prompt.** The only
  values accepted anywhere are three bounded scalars: a run-history limit, a run
  count capped at ``MAX_RUNS_PER_REQUEST``, and an arm chosen from ``ARMS``.
* Every run executes one fixed runner path derived from the suite directory, in
  a subprocess, under ``RUN_TIMEOUT_SECONDS``. No shell.
* Results are written under ``evals/<suite-id>/results/``, which is Git-ignored.
* Static serving is rooted at ``docs/``, with two extra read-only mounts:
  ``/brand/`` for the Slalom brand assets and ``/vendor/`` for the bundled
  anime.js build. Both resolve and re-check the real path before opening, so a
  traversal cannot escape them.

Honesty boundary
----------------
Every figure this server hands the page is either measured or explicitly absent
with the reason attached. It never substitutes a plausible number:

* Cost, time and consistency come from the telemetry CLI under ``evals/lib/``.
  When it is unavailable the endpoint reports the absence and the reason.
* ``estimated_usd`` and ``credits.total`` stay nullable. A Codex run on a model
  with no published rate has no cost figure, and ``0.0`` there is a false claim
  rather than a missing one.
* ``/api/metrics/<suite>`` returns the metric catalogue: every metric Calvin
  asked for, the quote that asked for it, and whether this harness measures it.
  The page renders that list rather than deciding for itself what is missing, so
  a gap cannot be quietly dropped from the UI.

Endpoints
---------
GET  /api/suites                        discovered suites, or why there are none
GET  /api/suite/<suite-id>              suite plan, taxonomy and task contracts
GET  /api/runs/<suite-id>?limit=k       run history, newest first
GET  /api/summary/<suite-id>            aggregate summary + telemetry availability
GET  /api/metrics/<suite-id>            the metric catalogue with measured/absent status
GET  /api/paste/<suite-id>              the harness's paste-ready workflow block
GET  /api/results/<suite-id>            the latest run record only
POST /api/run/<suite-id>                run the suite k times in one arm
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
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EVALS = ROOT / "evals"
SKILLS = ROOT / "skills"

BRAND_ROOT = SKILLS / "slalom-branding" / "assets"
VENDOR_ROOT = SKILLS / "animejs" / "assets" / "vendor"

# A suite id is a directory name. Constrained so it can never be a path.
SUITE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

RUN_TIMEOUT_SECONDS = 90
CLI_TIMEOUT_SECONDS = 60
MAX_RUNS_PER_REQUEST = 10
MAX_REQUEST_BODY_BYTES = 1024
RUN_LOCK = threading.Lock()

AGGREGATE_MODULE = "evals.lib.aggregate"
TELEMETRY_MODULE = "evals.lib.telemetry"
EMIT_MODULE = "evals.lib.emit_summary"

RUN_RECORD_SCHEMA = "ascent.eval-run-record.v1"
SUITE_SUMMARY_SCHEMA = "ascent.eval-suite-summary.v1"
DEFAULT_ARM = "with-skills"
COMPARISON_ARM = "baseline-no-skills"
ARMS = (DEFAULT_ARM, COMPARISON_ARM)

RATE_CARD_FILE = ROOT / "evals" / "lib" / "telemetry" / "codex_rates.json"

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

NO_SUITE_REASON = (
    "No evaluation suite is present in this checkout. A suite is a directory under "
    "evals/ containing an eval-plan.json and a run_deterministic.py runner. The "
    "telemetry harness under evals/lib/ is installed and its endpoints work, but "
    "there is nothing for it to aggregate until a suite lands."
)
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
    "No {0} runs exist for this suite. The comparison arm needs the same task attempted "
    "without the Ascent skills, which requires a model-driven suite; a deterministic "
    "script harness has no meaningful no-skills arm.".format(COMPARISON_ARM)
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

FALLBACK_REASONS = {
    "cost": NO_MODEL_REASON,
    "human_baseline_minutes": NO_BASELINE_REASON,
    "comparison_arm": NO_COMPARISON_ARM_REASON,
    "golden_comparison": NO_GOLDEN_REASON,
    "behavior": NO_BEHAVIOR_REASON,
    "consistency": NO_MODEL_REASON,
}


# ------------------------------------------------------------ metric catalogue

# Every metric Calvin asked for, with the quote that asked for it, transcribed
# from the recordings rather than paraphrased. The page renders this list, so a
# metric cannot be quietly dropped from the UI: if the harness cannot measure
# one, it appears here as absent with the reason.
#
# Sources:
#   2026-08-21 evals discussion  - Andrew Fischer, Calvin O'Keefe, Gada Lam.
#                                  Primary source for the metric triad.
#   2026-08-24 standup           - Calvin describing this interface itself.
#   2026-08-20 standup           - the credit figures from his own PowerPoint runs.
#   2026-08-17 standup           - why repeated self-review is the expensive part.
#
# `measured_from` names the run-record or summary path that carries the figure.
# `absent_reason` is the fallback when that path holds nothing and the run record
# does not supply its own account.
METRIC_CATALOGUE: Tuple[Dict[str, Any], ...] = (
    {
        "id": "correctness",
        "question": 1,
        "label": "Did it do the right thing",
        "unit": "pass / fail",
        "quote": (
            "those are two two of the important metrics, and the third one is, and it "
            "did the right thing, right? So, like, if we can validate those three "
            "things somehow, I feel like that is our test suite, or that's like our ... "
            "sales pitch"
        ),
        "source": "2026-08-21 evals discussion",
        "measured_from": "correctness.outcome",
    },
    {
        "id": "expected_output",
        "question": 1,
        "label": "Did it produce the output we expected",
        "unit": "checks passed of total",
        "quote": "Did it actually generate the output we anticipated it would generate?",
        "source": "2026-08-24 standup",
        "measured_from": "correctness.checks_passed",
    },
    {
        "id": "golden_comparison",
        "question": 1,
        "label": "Does it match what a human produced from the same input",
        "unit": "sections present of required",
        "quote": (
            "We need to be able to validate that the template that it outputs ... "
            "matches the template that a human is able to put together based on the "
            "same unstructured content. That'll be a much harder problem to solve."
        ),
        "source": "2026-08-24 standup",
        "measured_from": "correctness.golden_comparison",
        "absent_reason": NO_GOLDEN_REASON,
    },
    {
        "id": "human_review",
        "question": 1,
        "label": "Human review of the output",
        "unit": "reviewer verdict",
        "quote": (
            "Then we go and do like a little human review of that output. Are all three "
            "of those with the skill good? Is the one without the skill bad, right?"
        ),
        "source": "2026-08-24 standup",
        "measured_from": "correctness.human_review",
        "absent_reason": (
            "A human review verdict is entered by a person, not measured by the harness. "
            "Nothing here will ever fill it in: a generated verdict would be exactly the "
            "vibes metric this replaces."
        ),
    },
    {
        "id": "skills_invoked",
        "question": 1,
        "label": "Did it call all the skills it needed to call",
        "unit": "skills invoked vs expected",
        "quote": (
            "did it call all the skills it needs to call? Did it ask the right questions "
            "it needs to ask to the user?"
        ),
        "source": "2026-08-21 evals discussion",
        "measured_from": "behavior.skills_invoked",
        "absent_reason": NO_BEHAVIOR_REASON,
    },
    {
        "id": "questions_asked",
        "question": 1,
        "label": "Did it ask the right questions",
        "unit": "questions asked vs required",
        "quote": "Did it ask the right questions it needs to ask to the user?",
        "source": "2026-08-21 evals discussion",
        "measured_from": "behavior.clarifying_questions_asked",
        "absent_reason": NO_BEHAVIOR_REASON,
    },
    {
        "id": "tokens",
        "question": 2,
        "label": "Tokens per run",
        "unit": "tokens",
        "quote": (
            "to build this deck, we use this many tokens and it took this long. I feel "
            "like those two metrics are the ... two of the important metrics"
        ),
        "source": "2026-08-21 evals discussion",
        "measured_from": "cost.total_tokens",
        "absent_reason": NO_MODEL_REASON,
    },
    {
        "id": "tool_tokens",
        "question": 2,
        "label": "Cache and tool token split",
        "unit": "tokens by channel",
        "quote": (
            "without doing it non-deterministically and having it go re-review every "
            "section and re-input every token plus all of the tool token information"
        ),
        "source": "2026-08-21 evals discussion",
        "measured_from": "cost.cache_read_tokens",
        "absent_reason": NO_MODEL_REASON,
    },
    {
        "id": "credits",
        "question": 2,
        "label": "Credits per run",
        "unit": "credits (derived)",
        "quote": (
            "when you do like the PowerPoint one, is it 70 credits one time and 40 "
            "credits another time?"
        ),
        "source": "2026-08-21 evals discussion",
        "measured_from": "cost.credits.total",
        "absent_reason": (
            "Credits are the Codex billing unit, derived from measured tokens and the "
            "published rate card. A run has no credit figure when it was not a Codex "
            "run, or when its turn model is not on the rate card."
        ),
    },
    {
        "id": "cost_spread",
        "question": 2,
        "label": "How different is the cost between runs",
        "unit": "coefficient of variation",
        "quote": (
            "is it as token efficient in between runs? Like how different is the cost "
            "between each run?"
        ),
        "source": "2026-08-21 evals discussion",
        "measured_from": "summary.total_tokens.coefficient_of_variation",
        "absent_reason": (
            "A spread needs at least two runs in the same arm. One run has no spread, and "
            "reporting 0.0 off a single data point would read as perfect predictability."
        ),
    },
    {
        "id": "usd",
        "question": 2,
        "label": "Dollars per run",
        "unit": "USD",
        "quote": "the real value of what we're building is consistency and cost savings",
        "source": "2026-08-21 evals discussion",
        "measured_from": "cost.estimated_usd",
        "absent_reason": (
            "No dollar rate is on file for this run's model. Codex runs non-Anthropic "
            "models, and $0.00 there would be a false cost claim rather than a missing one."
        ),
    },
    {
        "id": "model_effort",
        "question": 2,
        "label": "Which model and effort the cost came from",
        "unit": "model, reasoning effort",
        "quote": (
            "I had Luna do it on medium reasoning and it took ... one of my credits for "
            "the month ... So then I switched to Tara on Medium and it took 70 credits"
        ),
        "source": "2026-08-20 standup",
        "measured_from": "host.model",
    },
    {
        "id": "model_requests",
        "question": 2,
        "label": "Model requests per turn",
        "unit": "requests per turn",
        "quote": (
            "when you do like the PowerPoint one, is it 70 credits one time and 40 "
            "credits another time?"
        ),
        "source": "2026-08-21 evals discussion; rate card measurement 2026-08-25",
        "measured_from": "cost.credits.requests_per_turn",
        "absent_reason": (
            "A Codex figure. It matters because the published credit band is per turn, so "
            "a per-request figure understates the bill by the requests-per-turn factor."
        ),
    },
    {
        "id": "context_utilization",
        "question": 2,
        "label": "Peak context used",
        "unit": "share of the context window",
        "quote": (
            "I think it like just looks over and over and over at the PowerPoint to be "
            "like, does it look good? ... it's again quite expensive"
        ),
        "source": "2026-08-20 and 2026-08-17 standups",
        "measured_from": "cost.peak_context_utilization",
        "absent_reason": (
            "Peak context needs a per-request input-token figure and the model's context "
            "window. One of the two was not recorded for this run."
        ),
    },
    {
        "id": "budget_share",
        "question": 2,
        "label": "Share of the credit budget",
        "unit": "percent of budget",
        "quote": "that was 24% of the budget used that day. Which is crazy high.",
        "source": "2026-08-21 evals discussion",
        "measured_from": "cost.credits.budget_share",
        "absent_reason": (
            "A budget share needs the size of the plan's credit allowance, which is "
            "account state and appears in no session log. Credits per run are measured; "
            "the denominator is not available to this harness."
        ),
    },
    {
        "id": "reproducibility",
        "question": 2,
        "label": "Same input, same output",
        "unit": "verdict across repeats",
        "quote": (
            "I think a lot of our focus going forward is 1 going to be on the eval stuff "
            "to prove that like what gets created is consistent."
        ),
        "source": "2026-08-20 standup",
        "measured_from": "determinism.verdict",
        "absent_reason": (
            "Reproducibility is measured by comparing repeated runs of the same input. "
            "This suite's run records carry no determinism block, so no comparison was "
            "made. It is a separate claim from cost predictability and is never a "
            "substitute for one."
        ),
    },
    {
        "id": "hermeticity",
        "question": 2,
        "label": "Was the run isolated",
        "unit": "workspace, network, clock",
        "quote": (
            "maybe if we set it up so that you can like point it towards a specific "
            "folder and sandbox it so that, you know, it only has access to those skills "
            "in that folder"
        ),
        "source": "2026-08-24 standup",
        "measured_from": "hermeticity",
        "absent_reason": (
            "This suite's run records carry no hermeticity block, so how isolated the run "
            "was is unrecorded."
        ),
    },
    {
        "id": "wall_clock",
        "question": 3,
        "label": "How long the run took",
        "unit": "seconds",
        "quote": "Cost. of time, like how long it takes.",
        "source": "2026-08-24 standup",
        "measured_from": "time.agent_wall_clock_seconds",
    },
    {
        "id": "average_execution_time",
        "question": 3,
        "label": "Average execution time across runs",
        "unit": "seconds",
        "quote": "And then looking at, you know, the average execution time",
        "source": "2026-08-24 standup",
        "measured_from": "summary.wall_clock_seconds.p50",
        "absent_reason": "An average across runs needs more than one run in the arm.",
    },
    {
        "id": "skill_call_duration",
        "question": 3,
        "label": "How long each skill call took",
        "unit": "seconds per call",
        "quote": (
            "Did that skill call out? How long did that skill call out take? Or how long "
            "did the full conversation take as compared to one that didn't have that skill?"
        ),
        "source": "2026-08-24 standup",
        "measured_from": "time.skill_call_seconds_by_skill",
        "absent_reason": (
            "Per-call timing needs a tool call and a matching tool result, each with a "
            "timestamp. Claude Code records both. Codex records the call but not the "
            "result time, so a Codex run has no per-call figure."
        ),
    },
    {
        "id": "human_baseline",
        "question": 3,
        "label": "How long it takes a human",
        "unit": "minutes",
        "quote": (
            "this PowerPoint, it took us this many hours or days to put it together. Now, "
            "the agent puts it together in this amount of time"
        ),
        "source": "2026-08-21 evals discussion",
        "measured_from": "time.human_baseline_minutes",
        "absent_reason": NO_BASELINE_REASON,
    },
    {
        "id": "hours_saved",
        "question": 3,
        "label": "Hours saved versus doing it manually",
        "unit": "minutes",
        "quote": (
            "it puts in some metric around hours saved versus doing it manually. And I "
            "think we can, instead of it just being some like vague, like, oh, it feels "
            "like it took an 8 point story to a 5 point story."
        ),
        "source": "2026-08-21 evals discussion",
        "measured_from": "time.time_saved_minutes",
        "absent_reason": (
            "Time saved is the human baseline minus the agent's wall clock. With no "
            "recorded baseline there is no saving to report, and it must never be derived "
            "from the agent's own run."
        ),
    },
    {
        "id": "skill_vs_no_skill",
        "question": 3,
        "label": "With the skill versus without it",
        "unit": "delta",
        "quote": (
            "there's some metric that we're comparing those runs against, you know, runs "
            "that didn't have that skill ... Are all three of those with the skill good? "
            "Is the one without the skill bad, right?"
        ),
        "source": "2026-08-24 standup",
        "measured_from": "summary.deltas",
        "absent_reason": NO_COMPARISON_ARM_REASON,
    },
    {
        "id": "failed_run_cost",
        "question": 3,
        "label": "What the failures cost",
        "unit": "tokens on failed runs",
        "quote": (
            "I tried to do Luna on Medium for like a PowerPoint with a known good "
            "template and it took like 30 something and it didn't work."
        ),
        "source": "2026-08-20 standup",
        "measured_from": "summary.failed_run_cost",
        "absent_reason": (
            "Needs at least one failed run carrying cost telemetry. A suite where every "
            "run passes has no failure cost to show, which is a fact rather than a gap."
        ),
    },
)


# --------------------------------------------------------------- suite objects


class Suite:
    """One discovered evaluation suite. Every path is derived, never supplied."""

    def __init__(self, suite_id: str, directory: Path) -> None:
        self.id = suite_id
        self.dir = directory
        self.plan_file = directory / "eval-plan.json"
        self.tasks_file = directory / "cases" / "tasks.jsonl"
        self.runner = directory / "run_deterministic.py"
        self.results_dir = directory / "results"
        self.runs_dir = self.results_dir / "runs"
        self.summary_file = self.results_dir / "latest.json"
        self.baseline_file = directory / "human-baseline.json"

    @property
    def runnable(self) -> bool:
        return self.runner.is_file()

    def aggregate_command(self) -> str:
        return "python3 -m {0} --suite {1}".format(AGGREGATE_MODULE, self.id)

    def emit_command(self) -> str:
        return "python3 -m {0} --suite {1}".format(EMIT_MODULE, self.id)


def discover_suites() -> Dict[str, Suite]:
    """Suites present in this checkout, keyed by id.

    A suite is a directory under evals/ holding an eval-plan.json. `evals/lib` is
    the harness rather than a suite and is skipped. Discovery *is* the allowlist:
    a request naming anything not in here is refused with 404.
    """
    found: Dict[str, Suite] = {}
    if not EVALS.is_dir():
        return found
    for entry in sorted(EVALS.iterdir()):
        if not entry.is_dir() or entry.name == "lib" or entry.name.startswith("."):
            continue
        if not SUITE_ID_PATTERN.match(entry.name):
            continue
        if not (entry / "eval-plan.json").is_file():
            continue
        found[entry.name] = Suite(entry.name, entry)
    return found


def resolve_suite(suite_id: str) -> Optional[Suite]:
    if not SUITE_ID_PATTERN.match(suite_id or ""):
        return None
    return discover_suites().get(suite_id)


# --------------------------------------------------------------------------- io


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def suite_tasks(suite: Suite) -> List[dict]:
    if not suite.tasks_file.is_file():
        return []
    out = []
    for line in suite.tasks_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def suite_plan(suite: Suite) -> dict:
    try:
        plan = read_json(suite.plan_file)
    except (OSError, json.JSONDecodeError):
        return {}
    return plan if isinstance(plan, dict) else {}


def plan_reason(suite: Suite, key: str) -> str:
    """Why a block is absent, in the suite plan's own words where it has them."""
    plan = suite_plan(suite)
    questions = plan.get("questions") or {}
    gaps = {gap.get("id"): gap for gap in (plan.get("gaps") or []) if isinstance(gap, dict)}
    declared = plan.get("unmeasured") if isinstance(plan.get("unmeasured"), dict) else {}

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

    if isinstance(declared.get(key), str):
        return declared[key]
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


def consistency_thresholds(suite: Suite) -> dict:
    """The provisional bands, preferring the suite plan's recorded copy."""
    thresholds = dict(CONSISTENCY_THRESHOLDS)
    plan = suite_plan(suite)
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


def rate_card_provenance() -> dict:
    """The credit rate card's citation, so the page can label a derived figure.

    A credit number without its rate card and fetch date is an assertion. With
    them it is a derivation a reader can check, which is the whole difference
    between this and the "vibes thing" Calvin wanted replaced.
    """
    try:
        card = read_json(RATE_CARD_FILE)
    except (OSError, json.JSONDecodeError):
        return {
            "available": False,
            "reason": "The Codex credit rate card is missing from {0}.".format(
                RATE_CARD_FILE.relative_to(ROOT)
            ),
        }
    source = card.get("source") or {}
    return {
        "available": True,
        "file": str(RATE_CARD_FILE.relative_to(ROOT)),
        "unit": card.get("unit"),
        "url": source.get("url"),
        "resolved_url": source.get("resolved_url"),
        "fetched": source.get("fetched"),
        "priced_models": sorted((card.get("rates") or {}).keys()),
        "unpriced_models": card.get("unpriced") or {},
        "unquantified_multipliers": card.get("unquantified_multipliers") or [],
        "billing_unit": (card.get("billing_unit_warning") or {}).get("correct_unit"),
        "billing_unit_why": (card.get("billing_unit_warning") or {}).get("why"),
        "derivation": (
            "Credits are derived, not reported: measured token deltas from the session "
            "log multiplied by the published rate card above."
        ),
    }


def suite_payload(suite: Suite) -> dict:
    tasks = suite_tasks(suite)
    plan = suite_plan(suite)
    latest = load_runs(suite, 1)["runs"]
    checks_total = None
    if latest:
        candidate = (latest[0].get("correctness") or {}).get("checks_total")
        if isinstance(candidate, int):
            checks_total = candidate
    payload = {
        "suite_id": suite.id,
        "plan": plan,
        "taxonomy": plan.get("taxonomy", {}),
        "tasks": tasks,
        # A check is not a task contract. The runner grades named checks across the
        # contracts and reports both counts; prefer its number and fall back to the
        # contract count only when no run has been recorded, saying which it is.
        "task_contracts_total": len(tasks),
        "checks_total": checks_total,
        "checks_total_source": (
            "latest run record" if checks_total is not None else "no run recorded yet"
        ),
        "runner": str(suite.runner.relative_to(ROOT)) if suite.runnable else None,
        "runnable": suite.runnable,
        "run_timeout_seconds": RUN_TIMEOUT_SECONDS,
        "max_runs_per_request": MAX_RUNS_PER_REQUEST,
        "arms": {"recorded": DEFAULT_ARM, "comparison": COMPARISON_ARM, "all": list(ARMS)},
        "consistency_thresholds": consistency_thresholds(suite),
        "rate_card": rate_card_provenance(),
    }
    if not tasks:
        payload["tasks_unavailable_reason"] = "No task contracts were found at {0}.".format(
            suite.tasks_file.relative_to(ROOT)
        )
    if not suite.runnable:
        payload["runnable_unavailable_reason"] = (
            "This suite has no runner at {0}, so the workbench cannot start a run for "
            "it. Existing run records are still readable.".format(
                suite.runner.relative_to(ROOT)
            )
        )
    return payload


def load_runs(suite: Suite, limit: Optional[int] = None) -> dict:
    if not suite.runs_dir.exists():
        return {
            "runs": [],
            "total_recorded": 0,
            "reason": "No run has been recorded yet. Results appear here after the first run.",
        }
    records = []
    unreadable = []
    for path in sorted(suite.runs_dir.glob("*.json")):
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


# ------------------------------------------------------------------- telemetry


def module_available(module: str) -> bool:
    probe = (
        "import importlib.util, sys\n"
        "try:\n"
        "    spec = importlib.util.find_spec({0!r})\n".format(module)
        + "except Exception:\n"
        "    spec = None\n"
        "sys.exit(0 if spec else 1)\n"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", probe], cwd=ROOT, capture_output=True, text=True,
            timeout=20, check=False,
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


def aggregate_cli(suite: Suite) -> tuple:
    """Ask evals.lib.aggregate for the suite summary. Returns (summary, meta)."""
    command = suite.aggregate_command()
    meta = {"command": command, "available": False}
    if not module_available(AGGREGATE_MODULE):
        meta["reason"] = (
            "The telemetry CLI is not installed yet. `{0}` reports no module named "
            "{1}.".format(command, AGGREGATE_MODULE)
        )
        return None, meta
    try:
        completed = subprocess.run(
            [sys.executable, "-m", AGGREGATE_MODULE, "--suite", suite.id],
            cwd=ROOT, capture_output=True, text=True, timeout=CLI_TIMEOUT_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired:
        meta["reason"] = "`{0}` exceeded {1} seconds.".format(command, CLI_TIMEOUT_SECONDS)
        return None, meta
    except OSError as error:
        meta["reason"] = "`{0}` could not be started: {1}".format(command, error)
        return None, meta
    meta["available"] = True
    meta["exit_code"] = completed.returncode
    if completed.returncode != 0:
        meta["reason"] = "`{0}` exited {1}.".format(command, completed.returncode)
        meta["stderr"] = completed.stderr.strip()[:2000]
        return None, meta
    payload = last_json_object(completed.stdout)
    if isinstance(payload, dict) and isinstance(payload.get("summary"), dict):
        payload = payload["summary"]
    if not isinstance(payload, dict) or "arms" not in payload:
        # The documented invocation writes the summary to results/latest.json rather
        # than to stdout, so read back the file the command just refreshed.
        payload = summary_file(suite)
    if not isinstance(payload, dict) or "arms" not in payload:
        meta["reason"] = "`{0}` exited 0 but produced no {1} document.".format(
            command, SUITE_SUMMARY_SCHEMA
        )
        meta["stdout"] = completed.stdout.strip()[:2000]
        return None, meta
    return payload, meta


def summary_file(suite: Suite) -> Optional[dict]:
    if not suite.summary_file.exists():
        return None
    try:
        payload = read_json(suite.summary_file)
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict) and payload.get("schema_version") == SUITE_SUMMARY_SCHEMA:
        return payload
    return None


def paste_block(suite: Suite) -> dict:
    """Ask the harness for its paste-ready block. The page never invents this text."""
    command = suite.emit_command()
    meta: dict = {"command": command, "available": False, "markdown": None}
    if not module_available(EMIT_MODULE):
        meta["reason"] = "The telemetry CLI is not installed yet: no module named {0}.".format(
            EMIT_MODULE
        )
        return meta
    try:
        completed = subprocess.run(
            [sys.executable, "-m", EMIT_MODULE, "--suite", suite.id],
            cwd=ROOT, capture_output=True, text=True, timeout=CLI_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        meta["reason"] = "`{0}` failed: {1}".format(command, error)
        return meta
    meta["exit_code"] = completed.returncode
    if completed.returncode != 0 or not completed.stdout.strip():
        meta["reason"] = "`{0}` exited {1}. {2}".format(
            command, completed.returncode, completed.stderr.strip()[:600] or "No output."
        )
        return meta
    meta["available"] = True
    meta["markdown"] = completed.stdout.rstrip()
    return meta


def human_baseline(suite: Suite) -> Optional[dict]:
    """Return a recorded human baseline, or None. Never derived from a run.

    A baseline file that says `recorded: false` is not a baseline. It is read as
    absent, so nothing downstream can pair it with a machine runtime.
    """
    minutes = os.environ.get("ASCENT_HUMAN_BASELINE_MINUTES", "").strip()
    if minutes:
        try:
            value = float(minutes)
        except ValueError:
            value = None
        if value is not None and value > 0:
            source = os.environ.get("ASCENT_HUMAN_BASELINE_SOURCE", "").strip()
            return {
                "minutes": value,
                "source": source or "ASCENT_HUMAN_BASELINE_MINUTES environment variable",
            }
    candidates = [suite.baseline_file, suite.dir / "baseline" / "human-baseline.json"]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("recorded") is False:
            continue
        value = payload.get("human_baseline_minutes")
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            return {
                "minutes": float(value),
                "source": payload.get("human_baseline_source") or str(path.relative_to(ROOT)),
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
    """A numeric field, or None.

    `"not-applicable"` is a legitimate value in these records and is deliberately
    *not* coerced to a number. A suite with no model in the loop has no agent
    elapsed time, and treating that string as zero is how a fabricated speedup
    gets published.
    """
    section = record.get(block)
    if not isinstance(section, dict):
        return None
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def credit_total(record: dict) -> Optional[float]:
    cost = record.get("cost")
    if not isinstance(cost, dict):
        return None
    credits = cost.get("credits")
    if not isinstance(credits, dict):
        return None
    value = credits.get("total")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def determinism_view(runs: list) -> dict:
    """The determinism and hermeticity facts, kept strictly apart from cost.

    Rail A's design separates two claims that look alike and are not:
    reproducibility of an artifact, and predictability of a bill. A suite can be
    perfectly reproducible and say nothing at all about cost - which is exactly
    the case for a suite with no model in it. So this block never carries a
    number a reader could quote as a price or a saving, and the page renders it
    under its own heading.
    """
    latest = runs[0] if runs else None
    if not isinstance(latest, dict):
        return {
            "available": False,
            "reason": "No run has been recorded, so there is nothing to compare.",
        }
    determinism = latest.get("determinism")
    hermeticity = latest.get("hermeticity")
    if not isinstance(determinism, dict):
        return {
            "available": False,
            "reason": (
                "This suite's run records carry no determinism block. Reproducibility is "
                "measured by comparing repeated runs of the same input; a suite that does "
                "not do that comparison cannot report it."
            ),
        }
    view = {
        "available": True,
        "verdict": determinism.get("verdict"),
        "runs_compared": determinism.get("runs_compared"),
        "identical_before_normalisation": determinism.get("identical_before_normalisation"),
        "identical_after_declared_normalisation": determinism.get(
            "identical_after_declared_normalisation"
        ),
        "canonical_artifact_sha256": determinism.get("canonical_artifact_sha256"),
        "graded_artifact_count": determinism.get("graded_artifact_count"),
        "declared_volatility": determinism.get("declared_volatility"),
        "undeclared_variation": determinism.get("undeclared_variation"),
        "separation_note": (
            "Reproducibility of an artifact is not predictability of a bill. This block "
            "makes no cost claim and must not be quoted as one."
        ),
    }
    if isinstance(hermeticity, dict):
        view["hermeticity"] = hermeticity
    else:
        view["hermeticity_unavailable_reason"] = (
            "This suite's run records carry no hermeticity block."
        )
    return view


def fallback_summary(suite: Suite, runs: list) -> Optional[dict]:
    """Summarise the run records on disk.

    Used only when evals.lib.aggregate is unavailable. Every figure comes from a
    measured field; blocks with no measurements are omitted with a reason rather
    than zero-filled.
    """
    if not runs:
        return None
    arms: dict = {}
    for record in runs:
        arms.setdefault(record.get("arm") or "unrecorded", []).append(record)

    summary = {
        "schema_version": SUITE_SUMMARY_SCHEMA,
        "suite_id": suite.id,
        "generated_at": iso_now(),
        "runs_per_arm": max(len(group) for group in arms.values()),
        "arms": {},
        "computed_by": "workbench-fallback",
    }
    for arm, group in sorted(arms.items()):
        outcomes = [str(item.get("correctness", {}).get("outcome", "")) for item in group]
        graded = [value for value in outcomes if value in {"pass", "fail"}]
        tokens = [v for v in (measured(i, "cost", "total_tokens") for i in group) if v is not None]
        dollars = [v for v in (measured(i, "cost", "estimated_usd") for i in group) if v is not None]
        credits = [v for v in (credit_total(i) for i in group) if v is not None]
        seconds = [
            v for v in (measured(i, "time", "agent_wall_clock_seconds") for i in group)
            if v is not None
        ]
        block: dict = {"runs": len(group), "run_count": len(group)}
        if graded:
            block["correctness_pass_rate"] = graded.count("pass") / len(graded)
        token_spread = spread(tokens, with_cv=True)
        if token_spread:
            block["total_tokens"] = token_spread
            verdict = consistency_verdict(token_spread.get("coefficient_of_variation"))
            if verdict:
                block["consistency_verdict"] = verdict
            else:
                block["consistency_verdict"] = "insufficient-runs"
                block["consistency_unavailable_reason"] = (
                    "A spread needs at least two runs with token telemetry in the same arm."
                )
        else:
            # Distinct from "too few runs": there are runs, they simply carry no
            # cost data. Telling the reader to run it again would never help.
            block["consistency_verdict"] = "no-cost-data"
            block["consistency_unavailable_reason"] = plan_reason(suite, "consistency")
        dollar_spread = spread(dollars)
        if dollar_spread:
            block["estimated_usd"] = dollar_spread
        credit_spread = spread(credits, with_cv=True)
        if credit_spread:
            block["credits"] = credit_spread
            block["credits_consistency_verdict"] = consistency_verdict(
                credit_spread.get("coefficient_of_variation")
            )
        wall_spread = spread(seconds, with_cv=True)
        if wall_spread:
            block["wall_clock_seconds"] = wall_spread
        else:
            block["wall_clock_unavailable_reason"] = (
                "No run in this arm recorded an agent elapsed time. A suite with no model "
                "in the loop has none; the harness runtime is a machine-speed figure and "
                "is not a substitute."
            )
        failed = [i for i in group if str(i.get("correctness", {}).get("outcome")) == "fail"]
        failed_tokens = [
            v for v in (measured(i, "cost", "total_tokens") for i in failed) if v is not None
        ]
        if failed_tokens:
            block["failed_run_cost"] = {
                "failed_runs": len(failed),
                "total_tokens": sum(failed_tokens),
                "note": "Tokens spent on runs that did not produce a passing output.",
            }
        summary["arms"][arm] = block

    left = summary["arms"].get(DEFAULT_ARM, {})
    right = summary["arms"].get(COMPARISON_ARM, {})
    deltas: dict = {}
    for key, source in (
        ("tokens_saved_p50", "total_tokens"),
        ("usd_saved_p50", "estimated_usd"),
        ("credits_saved_p50", "credits"),
    ):
        if source in left and source in right:
            deltas[key] = right[source]["p50"] - left[source]["p50"]
    if "wall_clock_seconds" in left and "wall_clock_seconds" in right:
        deltas["minutes_saved_p50"] = (
            right["wall_clock_seconds"]["p50"] - left["wall_clock_seconds"]["p50"]
        ) / 60
    if "correctness_pass_rate" in left and "correctness_pass_rate" in right:
        deltas["correctness_pass_rate_delta"] = (
            left["correctness_pass_rate"] - right["correctness_pass_rate"]
        )
    if deltas:
        summary["deltas"] = deltas
    else:
        summary["deltas_unavailable_reason"] = plan_reason(suite, "comparison_arm")
    return summary


def summary_payload(suite: Suite) -> dict:
    runs = load_runs(suite)["runs"]
    aggregate, aggregate_meta = aggregate_cli(suite)
    source = None
    summary = aggregate
    if summary is not None:
        source = AGGREGATE_MODULE
    else:
        summary = summary_file(suite)
        if summary is not None:
            source = str(suite.summary_file.relative_to(ROOT))
        else:
            summary = fallback_summary(suite, runs)
            if summary is not None:
                source = "workbench-fallback"
    return {
        "suite_id": suite.id,
        "summary": summary,
        "source": source,
        "consistency_thresholds": consistency_thresholds(suite),
        "rate_card": rate_card_provenance(),
        "determinism": determinism_view(runs),
        "telemetry": {"aggregate": aggregate_meta},
        "unmeasured": {
            "cost": plan_reason(suite, "cost"),
            "human_baseline_minutes": plan_reason(suite, "human_baseline_minutes"),
            "comparison_arm": plan_reason(suite, "comparison_arm"),
            "consistency": plan_reason(suite, "consistency"),
            "golden_comparison": plan_reason(suite, "golden_comparison"),
            "behavior": plan_reason(suite, "behavior"),
        },
        "runs_considered": len(runs),
        "summary_unavailable_reason": (
            None
            if summary is not None
            else "No run has been recorded for this suite, so there is nothing to aggregate."
        ),
    }


# ----------------------------------------------------------- metric catalogue


def _dig(payload: Any, path: str) -> Any:
    node = payload
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _has_value(value: Any) -> bool:
    """True when a figure is genuinely present.

    `"not-applicable"` and `"not-recorded"` are the harness's own words for a
    figure that does not exist, so they read as absent rather than as a string
    that happens to be non-empty.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value) and value not in ("not-applicable", "not-recorded", "unknown")
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def metrics_payload(suite: Suite) -> dict:
    """Every metric Calvin asked for, with its quote and its measured/absent status.

    Status is read off the data, not asserted: `measured` when the named path
    holds a value on the latest run or in the suite summary, `absent` otherwise,
    always with a reason. The page renders this rather than deciding for itself
    what to hide, so a metric cannot silently disappear from the UI.
    """
    history = load_runs(suite, 1)
    latest = history["runs"][0] if history["runs"] else None
    summary_block = summary_payload(suite)
    summary = summary_block.get("summary") or {}
    treated = ((summary.get("arms") or {}).get(DEFAULT_ARM)) or {}

    entries = []
    measured_count = 0
    for metric in METRIC_CATALOGUE:
        path = metric["measured_from"]
        if path.startswith("summary."):
            value = _dig(treated, path[len("summary."):])
            container = "suite summary, {0} arm".format(DEFAULT_ARM)
        else:
            value = _dig(latest or {}, path)
            container = "latest run record"
        present = _has_value(value)
        entry = {
            "id": metric["id"],
            "question": metric["question"],
            "label": metric["label"],
            "unit": metric["unit"],
            "quote": metric["quote"],
            "source": metric["source"],
            "measured_from": path,
            "read_from": container,
            "status": "measured" if present else "absent",
        }
        if present:
            measured_count += 1
            entry["value"] = value if not isinstance(value, (dict, list)) else None
        else:
            reason = None
            if isinstance(value, str) and value in ("not-applicable", "not-recorded", "unknown"):
                # The harness said so itself, in its own words.
                reason = "The harness recorded this as {0!r}.".format(value)
            if reason is None and latest is None and not path.startswith("summary."):
                reason = "No run has been recorded for this suite yet."
            if reason is None and isinstance(latest, dict):
                declared = latest.get("unmeasured")
                if isinstance(declared, dict):
                    # The run record's own account wins over the catalogue default.
                    for key in (metric["id"], path.split(".")[-1], path.split(".")[0]):
                        if isinstance(declared.get(key), str):
                            reason = declared[key]
                            break
            if reason is None:
                reason = metric.get("absent_reason") or "Not recorded by this suite."
            entry["absent_reason"] = reason
        entries.append(entry)

    return {
        "suite_id": suite.id,
        "generated_at": iso_now(),
        "metrics": entries,
        "measured": measured_count,
        "absent": len(entries) - measured_count,
        "total": len(entries),
        "provenance": (
            "Each metric is traced to the conversation that asked for it. Status is read "
            "from the recorded data, never asserted."
        ),
        "rate_card": rate_card_provenance(),
    }


# ---------------------------------------------------------------------- runner


def _records_from_runner(suite: Suite, reported: dict) -> List[dict]:
    """Load the run records the runner wrote, by the paths it reported.

    The runner owns the run record for its own suite. The workbench used to
    synthesise one from the runner's stdout, which meant two writers in one
    directory with the same id scheme, and a record whose `time` block described
    a Python subprocess rather than an agent. Reading the runner's own records
    instead removes the duplicate, and brings the `determinism`, `hermeticity`
    and per-check blocks with it.

    Paths are re-checked against the suite's results directory before opening:
    they come from a subprocess, so they are treated as untrusted even though the
    subprocess is ours.
    """
    reported_paths = reported.get("run_records")
    if not isinstance(reported_paths, list):
        return []
    try:
        base = suite.results_dir.resolve()
    except OSError:
        return []
    out: List[dict] = []
    for entry in reported_paths:
        if not isinstance(entry, str):
            continue
        try:
            candidate = Path(entry).resolve()
            candidate.relative_to(base)
        except (OSError, ValueError):
            continue
        if not candidate.is_file():
            continue
        try:
            record = read_json(candidate)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and record.get("schema_version") == RUN_RECORD_SCHEMA:
            out.append(record)
    return out


def _synthesised_record(
    suite: Suite, arm: str, reported: dict, process: dict, started_at: str,
    ended_at: str, harness_seconds: float,
) -> dict:
    """A minimal record for a runner that writes none of its own.

    Deliberately conservative about time. `agent_wall_clock_seconds` is
    "not-applicable", not the subprocess runtime: a suite with no model in the
    loop has no agent elapsed time, and pairing a machine-speed figure with a
    human baseline is how a four-hour baseline turns into a 7,000x speedup. The
    measured figure is still carried, under a name that says what it is, and
    nothing derives a saving from it.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    marker = "a" if arm == DEFAULT_ARM else "b"
    run_id = "{0}-{1}-{2}00-workbench".format(suite.id, stamp, marker)

    checks_total = reported.get("checks_total")
    if not isinstance(checks_total, int):
        checks_total = None
    passed = process.get("exit_code") == 0 and reported.get("outcome") == "pass"
    correctness: dict = {
        "outcome": "pass" if passed else "fail",
        "checks_total": checks_total,
        "failed_check_ids": list(reported.get("failed_check_ids") or []),
        "failed_task_ids": list(reported.get("failed_task_ids") or []),
    }
    if checks_total is None:
        correctness["checks_total_unavailable_reason"] = (
            "The runner did not report a check count. A task-contract count is not a "
            "check count, so none is substituted."
        )
    reported_passed = reported.get("checks_passed_min")
    if isinstance(reported_passed, int):
        correctness["checks_passed"] = reported_passed
    else:
        correctness["checks_passed"] = None
        correctness["checks_passed_unavailable_reason"] = (
            "This runner does not report how many checks passed. Read the process "
            "output below."
        )

    record: dict = {
        "schema_version": RUN_RECORD_SCHEMA,
        "run_id": run_id,
        "suite_id": suite.id,
        "arm": arm,
        "started_at": started_at,
        "ended_at": ended_at,
        "host": {
            "name": "python-deterministic-runner",
            "version": platform.python_version(),
            "model": None,
        },
        "correctness": correctness,
        "time": {
            # Not a number, on purpose. There is no agent, so there is no agent time.
            "agent_wall_clock_seconds": "not-applicable",
            "agent_wall_clock_unavailable_reason": (
                "No model is in the loop for this suite, so there is no agent elapsed "
                "time. The figure below is how long the harness process took, which is a "
                "machine-speed measurement and is never used to derive a saving."
            ),
            "harness_wall_clock_seconds": round(harness_seconds, 3),
        },
        "provenance": {
            "extraction": "deterministic",
            "telemetry_source": "workbench subprocess exit status",
            "session_path": None,
            "record_author": "workbench (the runner wrote no run_records)",
        },
        "unmeasured": {
            "cost": plan_reason(suite, "cost"),
            "golden_comparison": plan_reason(suite, "golden_comparison"),
            "behavior": plan_reason(suite, "behavior"),
            "human_baseline_minutes": plan_reason(suite, "human_baseline_minutes"),
            "agent_wall_clock_seconds": (
                "not-applicable: no model in the loop, so no agent elapsed time"
            ),
            "time_saved_minutes": (
                "Time saved needs an agent elapsed time and a recorded human baseline. "
                "This suite has neither, and the harness runtime is not a stand-in for "
                "the first."
            ),
        },
        "process": process,
    }
    return record


def run_batch(suite: Suite, count: int, arm: str) -> dict:
    """Run the suite `count` times and return the records the runner wrote.

    Calvin: "we can do, you know, do it over and over and over, and you can choose
    how many runs you want." One run cannot show a spread, and the spread is the
    claim, so the count is the point of this endpoint rather than a convenience.

    The count is passed to the runner as `--runs`, so the runner performs the
    repeats itself and can compare them. That is what makes a reproducibility
    verdict possible: comparing repeats is the measurement.
    """
    started_at = iso_now()
    started_monotonic = time.monotonic()
    timeout = RUN_TIMEOUT_SECONDS * max(count, 1)
    argv = [sys.executable, str(suite.runner), "--runs", str(int(count)), "--quiet"]
    timed_out = False
    try:
        completed = subprocess.run(
            argv, cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False,
        )
        stdout, stderr, exit_code = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = error.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        stderr = error.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        stderr += "\nRunner exceeded the {0} second timeout.".format(timeout)
        exit_code = None
    except OSError as error:
        stdout, stderr, exit_code = "", "runner could not be started: {0}".format(error), None
    harness_seconds = time.monotonic() - started_monotonic
    ended_at = iso_now()

    reported = last_json_object(stdout) or {}
    process = {
        "command": "python3 {0} --runs {1} --quiet".format(
            suite.runner.relative_to(ROOT), int(count)
        ),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "timeout_seconds": timeout,
        "stdout": stdout,
        "stderr": stderr,
    }

    records = _records_from_runner(suite, reported)
    record_author = "runner"
    if not records:
        records = [
            _synthesised_record(
                suite, arm, reported, process, started_at, ended_at, harness_seconds
            )
        ]
        record_author = "workbench-fallback"
        write_run_record(suite, records[0])

    payload = {
        "suite_id": suite.id,
        "arm": reported.get("arm") or arm,
        "requested": count,
        "completed": len(records),
        "record_author": record_author,
        "runs": records,
        "run": records[-1] if records else None,
        "runner_summary": reported,
        "process": process,
        "harness_wall_clock_seconds": round(harness_seconds, 3),
        "harness_wall_clock_note": (
            "How long the harness process took. A machine-speed figure, not an agent "
            "runtime, and never used to derive a time saving."
        ),
        "determinism": determinism_view(records),
    }
    if record_author == "workbench-fallback":
        payload["record_author_note"] = (
            "The runner reported no run_records, so the workbench wrote a minimal record "
            "from the process exit status. It carries no cost or agent-time figures."
        )
    if count < 2:
        payload["spread_note"] = (
            "One run has no spread. Ask for two or more to see how much the cost and time "
            "jump around, and to get a reproducibility verdict, which is a comparison "
            "between repeats."
        )
    return payload


def write_run_record(suite: Suite, record: dict) -> None:
    suite.runs_dir.mkdir(parents=True, exist_ok=True)
    target = suite.runs_dir / "{0}.json".format(record["run_id"])
    temporary = suite.runs_dir / ".{0}.tmp".format(record["run_id"])
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


# -------------------------------------------------------------- static mounts

STATIC_MOUNTS = {
    "brand": BRAND_ROOT,
    "vendor": VENDOR_ROOT,
}

CONTENT_TYPES = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".otf": "font/otf",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def resolve_mounted(mount: str, relative: str) -> Optional[Path]:
    """Resolve a path inside a read-only mount, or None if it escapes.

    Resolution happens before the file is opened and the real path is re-checked
    against the mount root, so `..`, a symlink, or an encoded separator cannot
    reach outside the mounted directory.
    """
    root = STATIC_MOUNTS.get(mount)
    if root is None or not root.is_dir():
        return None
    try:
        base = root.resolve(strict=True)
        target = (base / unquote(relative).lstrip("/")).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    if not target.is_file():
        return None
    try:
        target.relative_to(base)
    except ValueError:
        return None
    return target


# ---------------------------------------------------------------------- server


class WorkbenchHandler(SimpleHTTPRequestHandler):
    server_version = "AscentEvalWorkbench/3.0"

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

    def send_asset(self, path: Path) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type", CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def refuse_suite(self, suite_id: str) -> None:
        available = sorted(discover_suites())
        self.send_json(
            {
                "error": "Unknown suite.",
                "detail": "This workbench serves only suites discovered under evals/. "
                "Requested: {0!r}.".format(suite_id),
                "available_suites": available,
                "reason": None if available else NO_SUITE_REASON,
            },
            HTTPStatus.NOT_FOUND,
        )

    def limit_param(self, query: dict) -> Optional[int]:
        raw = (query.get("limit") or [""])[0]
        if not re.fullmatch(r"\d{1,3}", raw or ""):
            return None
        return max(1, min(int(raw), 100))

    def read_body(self) -> dict:
        """Parse a bounded JSON request body. Anything unparseable is an empty dict."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return {}
        if length <= 0 or length > MAX_REQUEST_BODY_BYTES:
            return {}
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8", "replace"))
        except (ValueError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def suites_payload(self) -> dict:
        suites = discover_suites()
        entries = []
        for suite_id in sorted(suites):
            suite = suites[suite_id]
            entries.append(
                {
                    "suite_id": suite_id,
                    "runnable": suite.runnable,
                    "task_contracts_total": len(suite_tasks(suite)),
                    "runs_recorded": load_runs(suite)["total_recorded"],
                }
            )
        payload = {
            "suites": entries,
            "default_suite": entries[0]["suite_id"] if entries else None,
            "max_runs_per_request": MAX_RUNS_PER_REQUEST,
            "arms": list(ARMS),
            "rate_card": rate_card_provenance(),
            "metric_catalogue_size": len(METRIC_CATALOGUE),
        }
        if not entries:
            payload["reason"] = NO_SUITE_REASON
            payload["harness"] = {
                "telemetry_module_available": module_available(TELEMETRY_MODULE),
                "aggregate_module_available": module_available(AGGREGATE_MODULE),
                "metric_catalogue_size": len(METRIC_CATALOGUE),
            }
        return payload

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        parts = [segment for segment in path.split("/") if segment]

        if parts and parts[0] in STATIC_MOUNTS:
            target = resolve_mounted(parts[0], "/".join(parts[1:]))
            if target is None:
                self.send_json({"error": "Not found.", "detail": path}, HTTPStatus.NOT_FOUND)
                return
            self.send_asset(target)
            return

        if not path.startswith("/api/"):
            super().do_GET()
            return

        try:
            if path == "/api/suites":
                self.send_json(self.suites_payload())
                return
            if len(parts) == 3 and parts[1] in {
                "suite", "runs", "summary", "results", "paste", "metrics",
            }:
                _, endpoint, suite_id = parts
                suite = resolve_suite(suite_id)
                if suite is None:
                    self.refuse_suite(suite_id)
                    return
                if endpoint == "suite":
                    self.send_json(suite_payload(suite))
                elif endpoint == "runs":
                    self.send_json(load_runs(suite, self.limit_param(query)))
                elif endpoint == "summary":
                    self.send_json(summary_payload(suite))
                elif endpoint == "metrics":
                    self.send_json(metrics_payload(suite))
                elif endpoint == "paste":
                    self.send_json(paste_block(suite))
                else:
                    history = load_runs(suite, 1)
                    self.send_json({"run": history["runs"][0] if history["runs"] else None})
                return
        except Exception as error:  # local tool: report the fault, do not fake data
            self.send_json(
                {"error": type(error).__name__, "detail": str(error)},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self.send_json({"error": "Unknown endpoint.", "detail": path}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parts = [segment for segment in urlparse(self.path).path.split("/") if segment]
        if len(parts) != 3 or parts[0] != "api" or parts[1] != "run":
            self.send_json({"error": "Unknown endpoint.", "detail": self.path}, HTTPStatus.NOT_FOUND)
            return
        suite = resolve_suite(parts[2])
        if suite is None:
            self.refuse_suite(parts[2])
            return
        body = self.read_body()

        count = body.get("runs", 1)
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            self.send_json(
                {
                    "error": "Invalid run count.",
                    "detail": "`runs` must be an integer between 1 and {0}.".format(
                        MAX_RUNS_PER_REQUEST
                    ),
                },
                HTTPStatus.BAD_REQUEST,
            )
            return
        if count > MAX_RUNS_PER_REQUEST:
            self.send_json(
                {
                    "error": "Too many runs requested.",
                    "detail": "`runs` is capped at {0} per request so one click cannot "
                    "occupy the server indefinitely.".format(MAX_RUNS_PER_REQUEST),
                },
                HTTPStatus.BAD_REQUEST,
            )
            return

        arm = body.get("arm", DEFAULT_ARM)
        if arm not in ARMS:
            self.send_json(
                {"error": "Unknown arm.", "detail": "`arm` must be one of {0}.".format(list(ARMS))},
                HTTPStatus.BAD_REQUEST,
            )
            return

        if not suite.runnable:
            self.send_json(
                {
                    "error": "Suite has no runner.",
                    "detail": "Expected a runner at {0}.".format(suite.runner.relative_to(ROOT)),
                },
                HTTPStatus.CONFLICT,
            )
            return

        if not RUN_LOCK.acquire(blocking=False):
            self.send_json({"error": "A suite is already running."}, HTTPStatus.CONFLICT)
            return
        try:
            self.send_json(run_batch(suite, count, arm))
        except Exception as error:
            self.send_json(
                {"error": type(error).__name__, "detail": str(error)},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        finally:
            RUN_LOCK.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local skill-evaluation workbench.")
    parser.add_argument("--port", type=int, default=8765, help="localhost port (default: 8765)")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), WorkbenchHandler)
    suites = sorted(discover_suites())
    print("Evaluation workbench: http://127.0.0.1:{0}/evals-workbench.html".format(args.port))
    if suites:
        print(
            "Suites discovered: {0}. Up to {1} runs per request.".format(
                ", ".join(suites), MAX_RUNS_PER_REQUEST
            )
        )
    else:
        print("No suite discovered under evals/. " + NO_SUITE_REASON)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping evaluation workbench.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

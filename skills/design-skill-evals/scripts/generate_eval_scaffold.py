#!/usr/bin/env python3
"""Create a framework-neutral Ascent evaluation scaffold from a profile JSON file.

The generated package answers three questions: did it do the job right, what did
it cost and was that predictable, and how much time did it save. Values that have
not been measured are written as "unknown" and listed as named gaps; nothing is
backfilled with a plausible-looking number.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

UNKNOWN = "unknown"

CONSISTENCY_THRESHOLDS = {
    "predictable": "< 0.10",
    "variable": "0.10-0.30",
    "unpredictable": "> 0.30",
}

RUN_RECORD_CONTRACT = {
    "schema_version": "ascent.eval-run-record.v1",
    "purpose": (
        "Machine-readable key contract for this suite's run records. It is a validator input, "
        "not an example record: it holds no measurements and no illustrative values, so it "
        "cannot be mistaken for data or copied into a report. Validate every record the harness "
        "writes against this file, and validate this file from the suite's acceptance test."
    ),
    "required_keys": [
        "schema_version", "run_id", "suite_id", "arm", "started_at", "ended_at",
        "host", "correctness", "cost", "time", "behavior", "provenance",
    ],
    "required_block_keys": {
        "host": ["name", "version", "model"],
        "correctness": ["outcome", "checks_total", "checks_passed", "failed_check_ids"],
        "cost": [
            "input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens",
            "total_tokens", "estimated_usd", "turns", "tool_calls",
        ],
        "time": ["agent_wall_clock_seconds"],
        "behavior": [
            "skills_invoked", "skills_expected", "missing_skill_invocations",
            "clarifying_questions_asked", "clarifying_questions_required",
        ],
        "provenance": ["telemetry_source", "session_path", "extraction"],
    },
    "arm_values": ["with-skills", "baseline-no-skills"],
    "correctness_outcome_values": ["pass", "fail"],
    "provenance_extraction_values": ["deterministic"],
    "omit_unless_recorded": [
        "correctness.golden_comparison",
        "time.human_baseline_minutes",
        "time.human_baseline_source",
        "time.time_saved_minutes",
        "time.speedup_factor",
    ],
    "nullable": ["cost.estimated_usd"],
    "absence_markers": {
        "unknown": "The field could be measured for this suite and has not been.",
        "not-applicable": "The field cannot exist for this suite's design. A sibling field ending in _note says why.",
        "not-observable": "Measuring it would need a session log or a user turn this suite does not produce. A sibling _note says why.",
    },
    "forbidden": (
        "A zero, an empty list or a plausible-looking default standing in for an unmeasured "
        "value. Use an absence marker or omit the key and name the gap."
    ),
}

SUITE_SUMMARY_CONTRACT = {
    "schema_version": "ascent.eval-suite-summary.v1",
    "purpose": (
        "Machine-readable key contract for the suite summary. Written only by "
        "`python3 -m evals.lib.aggregate`. Contains no values, for the same reason as the run "
        "record contract."
    ),
    "required_keys": ["schema_version", "suite_id", "generated_at", "runs_per_arm", "arms", "deltas"],
    "arm_keys": [
        "correctness_pass_rate", "total_tokens", "estimated_usd",
        "wall_clock_seconds", "consistency_verdict",
    ],
    "spread_keys": {
        "total_tokens": ["min", "p50", "p95", "max", "mean", "coefficient_of_variation"],
        "estimated_usd": ["min", "p50", "max"],
        "wall_clock_seconds": ["min", "p50", "max", "coefficient_of_variation"],
    },
    "delta_keys": [
        "tokens_saved_p50", "usd_saved_p50", "minutes_saved_p50",
        "correctness_pass_rate_delta", "consistency_improvement",
    ],
    "consistency_verdict_values": ["predictable", "variable", "unpredictable", "insufficient-runs", "unknown"],
    "consistency_thresholds_status": "provisional",
    "rules": [
        "A spread value that was not measured is null, never 0.",
        "An arm with fewer than three runs reports consistency_verdict insufficient-runs; do not compute a coefficient of variation from one or two runs.",
        "Every delta is null or \"unknown\" when either arm has no runs. A with-skills figure alone is not a saving.",
    ],
}


def read_profile(path: Path) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    required = {"skill_id", "purpose", "interfaces", "success_conditions"}
    missing = sorted(required - profile.keys())
    if missing:
        raise ValueError(f"profile is missing required fields: {', '.join(missing)}")
    return profile


def write_new(path: Path, text: str) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    write_new(path, json.dumps(payload, indent=2) + "\n")


def fill_contract_blocks(profile: dict) -> list[str]:
    """Add the v2 blocks the contract requires, marked unknown. Return the checklist."""
    todo: list[str] = []
    if "deliverable" not in profile:
        profile["deliverable"] = {
            "name": UNKNOWN,
            "kind": "document | structured-artifact | machine-local-state",
            "client_facing": UNKNOWN,
            "path_or_form": UNKNOWN,
        }
        todo.append("deliverable — name the artifact a human would otherwise produce")
    if "human_baseline" not in profile:
        profile["human_baseline"] = {
            "recorded": False,
            "minutes": UNKNOWN,
            "source": UNKNOWN,
            "note": "Record a timed manual run or a dated delivery-lead estimate. Never estimate this from an agent run.",
        }
        todo.append("human_baseline — no human effort recorded, so no time saving can be claimed")
    if "golden_reference" not in profile:
        profile["golden_reference"] = {
            "available": False,
            "reference_id": None,
            "owner": None,
            "note": "State whether a known-good human version of the deliverable exists, and who owns it.",
        }
        todo.append("golden_reference — confirm whether a known-good human document exists")
    if "expected_skill_invocations" not in profile:
        profile["expected_skill_invocations"] = []
        todo.append("expected_skill_invocations — list the skills a correct run must actually invoke")
    if "required_clarifying_questions" not in profile:
        profile["required_clarifying_questions"] = []
        todo.append("required_clarifying_questions — list what the agent must confirm with the user")
    if "failure_mode_provenance" not in profile:
        profile["failure_mode_provenance"] = "contract-enumeration"
        todo.append(
            "failure_mode_provenance — contract-enumeration means the failures were guessed "
            "from the design; run error analysis on real traces to replace it"
        )
    return todo


def build_plan(profile: dict) -> dict:
    skill_id = profile["skill_id"]
    baseline_recorded = bool(profile.get("human_baseline", {}).get("recorded"))
    golden_available = bool(profile.get("golden_reference", {}).get("available"))
    gaps = [
        {
            "id": "no-cost-data",
            "question": "cost",
            "statement": "No token or dollar figures have been recorded for this suite yet.",
            "unblocked_by": "Run the suite under the telemetry harness and aggregate the run records.",
        },
        {
            "id": "no-baseline-arm",
            "question": "cost",
            "statement": "The same task has not been run without the Ascent skills, so no saving can be reported.",
            "unblocked_by": "Add a baseline-no-skills run on the same host, model, prompt and fixture.",
        },
        {
            "id": "consistency-unknown",
            "question": "cost",
            "statement": "Cost consistency is unknown until the suite has been run at least three times per arm.",
            "unblocked_by": "Set runs_per_arm to at least three and aggregate the results.",
        },
        {
            "id": "reproducibility-unproven",
            "question": "correctness",
            "statement": "Nothing yet shows the same input produces the same output; the suite has not been repeated and its artifacts have not been hashed.",
            "unblocked_by": "Repeat the whole suite over one pinned fixture, hash every graded artifact, compare the runs, and declare every field allowed to vary.",
        },
    ]
    for gap in gaps:
        gap.setdefault("status", "open")
    if not baseline_recorded:
        gaps.append(
            {
                "status": "open",
                "id": "no-human-baseline",
                "question": "time",
                "statement": "No human effort has been recorded for this deliverable, so time saved cannot be claimed.",
                "unblocked_by": "One timed manual run, or a delivery-lead estimate with a date and a source.",
            }
        )
    if not golden_available:
        gaps.append(
            {
                "status": "open",
                "id": "no-golden-reference",
                "question": "correctness",
                "statement": "No known-good human version of the deliverable is registered, so correctness rests on assertions alone.",
                "unblocked_by": "Register an approved reference document with its required section list and owner.",
            }
        )
    return {
        "schema_version": "ascent.skill-eval-plan.v1",
        "skill_id": skill_id,
        "questions": {
            "correctness": {
                "status": "measured",
                "how": "Code-based assertions on the produced artifact"
                + (" plus a golden-document comparison." if golden_available else "; no golden reference registered."),
            },
            "cost": {"status": "not-instrumented", "how": UNKNOWN},
            "time": {"status": "not-instrumented", "how": UNKNOWN},
        },
        "arms": {
            "with-skills": {"status": "implemented", "note": "Ascent skill library and templates available."},
            "baseline-no-skills": {
                "status": "not-implemented",
                "note": "Same host, model, prompt and fixture with no Ascent skills. Add this before quoting any saving.",
            },
        },
        "runs_per_arm": 5,
        "consistency": {
            "metric": "coefficient_of_variation(total_tokens)",
            "verdict": UNKNOWN,
            "thresholds": CONSISTENCY_THRESHOLDS,
            "thresholds_status": "provisional",
            "note": "Fewer than three runs per arm cannot support a consistency verdict.",
        },
        "reproducibility": {
            "status": "unproven",
            "metric": "sha256 over the graded artifact bundle, compared across runs",
            "verdict": UNKNOWN,
            "declared_volatility": [],
            "note": (
                "Reproducibility of the output is a different claim from consistency of cost. "
                "Prove it by running the whole suite at least three times over one pinned fixture "
                "and comparing hashed artifacts. Enumerate every field allowed to vary, with its "
                "cause and what would close it, and fail the suite on any difference no declared "
                "rule explains."
            ),
        },
        "hermeticity": {
            "workspace": UNKNOWN,
            "environment": UNKNOWN,
            "network": UNKNOWN,
            "clock": UNKNOWN,
            "inputs": UNKNOWN,
            "note": (
                "Record what was actually controlled, and say plainly what was not. Network "
                "blocking counts only when it is enforced - an injected sitecustomize.py that "
                "raises on socket use - not when it is merely assumed."
            ),
        },
        "coverage": {
            "mode": "hybrid",
            "rationale": "Confirm this selection after reviewing supported behavior and its baseline.",
        },
        "trials": {
            "count": 1,
            "reliability_metric": "outcome_pass_rate",
            "rationale": "Increase only for variable behavior, and name pass@k or pass^k.",
        },
        "graders": [
            {"id": "outcome", "type": "code", "required": True, "rationale": "Start with observable outcomes."}
        ],
        "metrics": [
            "correctness_pass_rate",
            "evaluated_task_count",
            "failed_task_ids",
            "total_tokens",
            "estimated_usd",
            "wall_clock_seconds",
            "time_saved_minutes",
            "consistency_verdict",
        ],
        "gaps": gaps,
        "aggregation": {"command": f"python3 -m evals.lib.aggregate --suite {skill_id}"},
        "taxonomy": {
            "eval_type": "hybrid",
            "interaction_scope": "single-turn",
            "graded_surface": ["outcome"],
            "grader_types": ["code-based"],
            "scoring": "binary",
            "reliability_estimator": "single-trial",
            "execution_context": "ci-offline",
            "failure_mode_provenance": profile.get("failure_mode_provenance", "contract-enumeration"),
            "reference_dependence": "reference-based" if golden_available else "reference-free",
            "note": "Reference classification only. Confirm every value and keep it consistent with coverage.mode.",
        },
        "transcript_review": {"sample": "all failures and grader disagreements"},
    }


def build_readme(profile: dict, plan: dict, todo: list[str]) -> str:
    skill_id = profile["skill_id"]
    deliverable = profile.get("deliverable", {}).get("name", UNKNOWN)
    items = [f"- [ ] {item}" for item in todo]
    items += [
        f"- [ ] `{gap['id']}` (question {gap['question']}) — {gap['statement']} Closed by: {gap['unblocked_by']}"
        for gap in plan.get("gaps", [])
    ]
    items.append("- [ ] Replace every placeholder assertion in `cases/tasks.jsonl`.")
    checklist = "\n".join(items)
    return f"""# {skill_id} evaluations

Deliverable under evaluation: **{deliverable}**

This package answers three questions. Every one of them has to be answerable, or
the missing answer is recorded as a named gap in `eval-plan.json`.

| # | Question | Where the answer lives |
| - | -------- | ---------------------- |
| 1 | Did it do the job right? | `correctness` and `behavior` in each run record |
| 2 | What did it cost, and was that predictable? | `cost` per run, and the spread across runs in `results/latest.json` |
| 3 | How much time did it save? | `time` per run, against the human baseline in `baseline/human-baseline.json` |

Both arms are required before any saving is quoted: `with-skills` and
`baseline-no-skills` (the same job with no Ascent skills). A single-arm number is
not a saving.

## Run

```bash
python3 evals/{skill_id}/run_deterministic.py
python3 -m evals.lib.aggregate --suite {skill_id}
```

The aggregator reads `results/runs/*.json` and writes the
`ascent.eval-suite-summary.v1` summary to `results/latest.json`. Both are
Git-ignored.

## What this suite cannot tell you yet

{checklist}

`schemas/` holds key contracts, not example records: they list required keys,
permitted arms and permitted absence markers, and contain no values. Validate
every run record the harness writes against `schemas/run-record.contract.json`,
and fail the suite when one violates it.

Read the repository `design-skill-evals` skill and its
[evaluation contract](../../skills/design-skill-evals/references/evaluation-contract.md)
for the task, grading, cost and time contract. Every unmeasured value is
`"unknown"`, every value that cannot exist for this suite is `"not-applicable"`
or `"not-observable"` with a note saying why, and neither is ever replaced with a
plausible-looking number.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--inspect", action="store_true", help="Add an optional Inspect adapter placeholder.")
    args = parser.parse_args()

    profile = read_profile(args.profile)
    output = args.output
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing scaffold: {output}")

    todo = fill_contract_blocks(profile)
    plan = build_plan(profile)

    (output / "cases").mkdir(parents=True)
    (output / "results" / "runs").mkdir(parents=True)
    (output / "baseline").mkdir()
    (output / "schemas").mkdir()

    task = {
        "id": f"{profile['skill_id']}-positive-01",
        "case_type": "insufficient-information" if profile.get("unknowns") else "positive",
        "intent": "should-do",
        "prompt": "TODO: Write a passable, user-visible task.",
        "fixture": "TODO: Create an isolated fixture.",
        "expected_outcome": profile["success_conditions"],
        "must_not": [],
        "graded_surface": ["outcome"],
        "assertion_classes": ["TODO: name what each check asserts"],
        "scoring": "binary",
        "reference_solution": None,
        "graders": ["outcome"],
        "trials": 1,
        "missing_information": profile.get("unknowns", []),
    }

    run_record_contract = json.loads(json.dumps(RUN_RECORD_CONTRACT))
    suite_summary_contract = json.loads(json.dumps(SUITE_SUMMARY_CONTRACT))
    if profile.get("golden_reference", {}).get("available"):
        run_record_contract["required_block_keys"]["correctness"].append("golden_comparison")
        run_record_contract["omit_unless_recorded"].remove("correctness.golden_comparison")
    if profile.get("human_baseline", {}).get("recorded"):
        run_record_contract["required_block_keys"]["time"].append("human_baseline_minutes")

    human_baseline = {
        "deliverable": profile.get("deliverable", {}).get("name", UNKNOWN),
        "recorded": False,
        "minutes": UNKNOWN,
        "method": "timed-manual-run | delivery-lead-estimate | timesheet",
        "recorded_by": UNKNOWN,
        "recorded_on": UNKNOWN,
        "note": "Until this is recorded, the suite reports time saved as unknown. Never derive it from an agent run.",
    }

    write_json(output / "skill-profile.json", profile)
    write_json(output / "eval-plan.json", plan)
    write_new(output / "cases" / "tasks.jsonl", json.dumps(task) + "\n")
    write_json(output / "baseline" / "human-baseline.json", human_baseline)
    write_json(output / "schemas" / "run-record.contract.json", run_record_contract)
    write_json(output / "schemas" / "suite-summary.contract.json", suite_summary_contract)
    write_new(output / "README.md", build_readme(profile, plan, todo))
    write_new(output / ".gitignore", "results/\n")

    if args.inspect:
        inspect_dir = output / "inspect"
        inspect_dir.mkdir()
        write_new(
            inspect_dir / "README.md",
            "Map `cases/tasks.jsonl` to an Inspect Dataset, the target harness to a Solver or agent, "
            "outcome checks to Scorers, and isolated fixtures to a Sandbox. Pin the installed Inspect "
            "version and retain run logs for transcript review. Cost and time metrics still come from the "
            "deterministic telemetry harness, not from Inspect's own log summary.\n",
        )

    print(f"Created evaluation scaffold: {output}")
    print("Answer these before claiming coverage:")
    for item in todo or ["Replace every placeholder assertion."]:
        print(f"  - {item}")


if __name__ == "__main__":
    main()

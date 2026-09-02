#!/usr/bin/env python3
"""Validate the skill-evaluation contract, the scaffold generator and the run records.

Every assertion here is structural. An earlier version of this file asserted a
hardcoded slide count and broke on every rename; nothing below counts anything it
can instead derive from the artifact under test.
"""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "context-skills"
SKILLS_ROOT = ROOT / "plugins" / "ascent" / "skills"
GENERATOR = SKILLS_ROOT / "design-skill-evals" / "scripts" / "generate_eval_scaffold.py"
RUNNER = EVAL / "run_deterministic.py"
CONTRACT_DOC = SKILLS_ROOT / "design-skill-evals" / "references" / "evaluation-contract.md"
WORKBENCH_SERVER = ROOT / "docs" / "evals_workbench.py"

# The markers a package may use in place of a measured value. A plausible-looking
# number standing in for an unmeasured one is the failure mode this file guards
# against.
ABSENCE_MARKERS = {"unknown", "not-applicable", "not-observable", "not-recorded"}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_tasks() -> list:
    return [
        json.loads(line)
        for line in (EVAL / "cases" / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def check_metadata(profile: dict, plan: dict, tasks: list) -> None:
    check(profile["schema_version"] == "ascent.skill-eval-profile.v1", "profile schema version changed")
    check(plan["schema_version"] == "ascent.skill-eval-plan.v1", "plan schema version changed")
    check(plan["coverage"]["mode"] == "regression", "context suite should protect established behavior")
    check(plan["coverage"]["mode"] == plan["taxonomy"]["eval_type"], "coverage.mode and taxonomy.eval_type disagree")
    check({task["case_type"] for task in tasks} >= {"positive", "negative"}, "suite needs positive and negative cases")
    check(all(task["reference_solution"] for task in tasks), "task is missing a reference solution")
    check(all(task["trials"] == 1 for task in tasks), "deterministic fixture should run one trial")

    # runs_per_arm is a different thing from a task's trials, and a cross-run
    # claim needs repetition. Fewer than three repeats cannot support one.
    check(isinstance(plan["runs_per_arm"], int), "runs_per_arm must be an integer")
    check(plan["runs_per_arm"] >= 3, "runs_per_arm below 3 cannot support any cross-run claim")

    # Nothing may be reported as measured unless the plan says how.
    for question, block in plan["questions"].items():
        check("status" in block and "how" in block, "question {0} is missing status or how".format(question))
        if block["status"] == "measured":
            check(block["how"] != "unknown", "question {0} claims measured with how=unknown".format(question))
            check(bool(block.get("reported")), "question {0} claims measured but reports nothing".format(question))
        else:
            check(bool(block.get("note")), "unmeasured question {0} must carry a note".format(question))

    # Every gap names what would close it, and no gap is silently marked closed.
    gap_ids = [gap["id"] for gap in plan["gaps"]]
    check(len(gap_ids) == len(set(gap_ids)), "duplicate gap id in eval-plan.json")
    for gap in plan["gaps"]:
        for field in ("id", "question", "statement", "unblocked_by", "status"):
            check(bool(gap.get(field)), "gap {0!r} is missing {1}".format(gap.get("id"), field))
        check(
            "closed" not in gap["status"],
            "gap {0} is marked closed; a closed gap is deleted, not flagged".format(gap["id"]),
        )
        check(
            gap["question"] in plan["questions"],
            "gap {0} names an unknown question {1!r}".format(gap["id"], gap["question"]),
        )

    # The README has to name every gap, or the honest ledger is only machine-visible.
    readme = (EVAL / "README.md").read_text(encoding="utf-8")
    missing = [gap_id for gap_id in gap_ids if gap_id not in readme]
    check(not missing, "gaps absent from the suite README: {0}".format(missing))

    # The baseline arm must be accounted for, never quietly absent.
    baseline = plan["arms"]["baseline-no-skills"]
    check(baseline["status"] in {"implemented", "not-implemented", "not-applicable"}, "unknown baseline arm status")
    if baseline["status"] != "implemented":
        check(bool(baseline.get("note")), "an absent baseline arm must record why")

    # A human baseline is a recorded fact or an explicit absence. Never a guess.
    human = load_json(EVAL / "baseline" / "human-baseline.json")
    if human.get("recorded") is not True:
        check(human.get("minutes") == "unknown", "an unrecorded human baseline must say unknown, not a number")


def check_stale_paths() -> None:
    """`.codex/project-context/` was superseded by `workspace/.system/project-context/`."""
    for path in sorted(EVAL.rglob("*")):
        if path.is_file() and path.suffix in {".json", ".md", ".py", ".jsonl"}:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if ".codex/project-context" in line and "superseded" not in line:
                    raise AssertionError(
                        "{0} still uses the retired .codex path: {1}".format(path.relative_to(ROOT), line.strip())
                    )

    contract = CONTRACT_DOC.read_text(encoding="utf-8")
    check("Measure a specific skill by isolation" in contract, "contract does not define a skill-run cost boundary")
    check("workflow cost" in contract, "contract does not distinguish multi-skill workflow cost")
    check("not skill-run cost" in contract, "contract conflates tool-call duration with skill-run cost")


def check_run_record(record: dict, record_contract: dict, tasks: list, plan: dict) -> None:
    for key in record_contract["required_keys"]:
        check(key in record, "run record is missing {0}".format(key))
    for block, keys in record_contract["required_block_keys"].items():
        check(isinstance(record.get(block), dict), "run record block {0} is not an object".format(block))
        for key in keys:
            check(key in record[block], "run record is missing {0}.{1}".format(block, key))
    check(record["arm"] in record_contract["arm_values"], "run record arm {0!r} is not permitted".format(record["arm"]))
    check(record["provenance"]["extraction"] == "deterministic", "provenance.extraction must be deterministic")

    # Correctness totals are derived from the recorded checks, never asserted
    # against a literal count.
    correctness = record["correctness"]
    checks = correctness["checks"]
    check(correctness["checks_total"] == len(checks), "checks_total does not match the recorded checks")
    passed = [item for item in checks if item["outcome"] == "pass"]
    check(correctness["checks_passed"] == len(passed), "checks_passed does not match the recorded checks")
    failed = [item["id"] for item in checks if item["outcome"] != "pass"]
    check(correctness["failed_check_ids"] == failed, "failed_check_ids does not match the recorded checks")
    check(
        correctness["evaluated_task_count"] == len(tasks),
        "evaluated_task_count does not match the number of task contracts",
    )

    # Every check belongs to a declared task contract and names a term from the
    # contract's assertion-class vocabulary.
    permitted = set(
        term for term in CONTRACT_DOC.read_text(encoding="utf-8").split("`") if term and "\n" not in term
    )
    task_ids = {task["id"] for task in tasks}
    for item in checks:
        check(item["task_id"] in task_ids, "check {0} names an unknown task {1!r}".format(item["id"], item["task_id"]))
        check(
            item["assertion_class"] in permitted,
            "check {0} uses an assertion class absent from the contract: {1!r}".format(item["id"], item["assertion_class"]),
        )
        if item["outcome"] == "pass":
            check(
                "sentinel found" not in item["detail"] and "not selected:" not in item["detail"],
                "passing check {0} carries failure wording: {1!r}".format(item["id"], item["detail"]),
            )

    # Every task contract is covered by at least one check.
    covered = {item["task_id"] for item in checks}
    check(covered == task_ids, "task contracts with no check: {0}".format(sorted(task_ids - covered)))

    # Absent measurements use a declared marker. No zeros, no plausible defaults.
    markers = set(record_contract["absence_markers"]) | ABSENCE_MARKERS
    for field in ("input_tokens", "output_tokens", "total_tokens", "turns", "tool_calls"):
        value = record["cost"][field]
        check(value in markers, "cost.{0} is {1!r}; an unmeasurable field must use a marker".format(field, value))
    check(record["cost"]["estimated_usd"] is None, "estimated_usd must be null when no rate applies, never 0.0")
    check(record["time"]["agent_wall_clock_seconds"] in markers, "agent_wall_clock_seconds must use a marker")
    if load_json(EVAL / "baseline" / "human-baseline.json").get("recorded") is not True:
        for field in ("human_baseline_minutes", "time_saved_minutes", "speedup_factor"):
            check(field not in record["time"], "time.{0} present with no recorded human baseline".format(field))
    check("golden_comparison" not in correctness, "golden_comparison present with no registered reference document")
    for field in ("skills_invoked", "missing_skill_invocations", "clarifying_questions_asked"):
        check(record["behavior"][field] in markers, "behavior.{0} must use a marker here".format(field))

    # Provenance pins the inputs so a drifted script or fixture is visible.
    provenance = record["provenance"]
    check(len(provenance["case_fixture_sha256"]) == 64, "case fixture digest is not a sha256")
    check(bool(provenance["target_script_sha256"]), "run record does not pin the target scripts")
    check(
        all(len(digest) == 64 for digest in provenance["target_script_sha256"].values()),
        "a target script digest is not a sha256",
    )

    # The reproducibility claim must be backed by more than one run.
    determinism = record["determinism"]
    check(
        determinism["runs_compared"] == plan["runs_per_arm"],
        "determinism compared a different number of repeats than the plan declares",
    )
    check(determinism["runs_compared"] >= 3, "a reproducibility claim needs at least three runs")
    check(
        determinism["undeclared_variation"] == [],
        "undeclared non-determinism: {0}".format(determinism["undeclared_variation"]),
    )
    check(determinism["identical_after_declared_normalisation"] is True, "graded artifacts differ across runs")
    check(len(set(determinism["canonical_artifact_sha256"])) == 1, "canonical artifact digests differ across runs")
    check(determinism["graded_artifact_count"] > 0, "no graded artifact was hashed")
    for rule in determinism["declared_volatility"]:
        for field in ("id", "cause", "closed_by"):
            check(bool(rule.get(field)), "declared volatility rule {0!r} is missing {1}".format(rule.get("id"), field))


def check_runner(plan: dict, tasks: list) -> None:
    record_contract = load_json(EVAL / "schemas" / "run-record.contract.json")
    with tempfile.TemporaryDirectory(prefix="ascent-eval-runrecords-") as temp:
        results = Path(temp) / "results"
        completed = subprocess.run(
            [sys.executable, str(RUNNER), "--results-dir", str(results), "--quiet"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            completed.returncode == 0,
            "the determinism suite failed:\n{0}\n{1}".format(completed.stdout, completed.stderr),
        )
        summary = json.loads(completed.stdout.strip().splitlines()[-1])
        check(summary["outcome"] == "pass", "suite outcome was {0!r}".format(summary["outcome"]))
        check(summary["runs"] == plan["runs_per_arm"], "the runner ignored runs_per_arm from the plan")
        check(not summary["run_record_validation_problems"], "the runner wrote records that violate its own contract")

        written = sorted((results / "runs").glob("*.json"))
        check(len(written) == summary["runs"], "the runner did not write one run record per repeat")
        for path in written:
            check_run_record(load_json(path), record_contract, tasks, plan)

        # Legacy stdout keys the existing workbench still reads must survive.
        for key in ("suite", "outcome", "evaluated_task_count", "outcome_pass_rate", "failed_task_ids", "duration_ms"):
            check(key in summary, "the runner dropped the legacy summary key {0!r}".format(key))

    # A single run cannot support a reproducibility claim, and the record must say
    # so rather than presenting a trivially-identical result as evidence.
    with tempfile.TemporaryDirectory(prefix="ascent-eval-onerun-") as temp:
        completed = subprocess.run(
            [sys.executable, str(RUNNER), "--runs", "1", "--results-dir", str(Path(temp) / "results"), "--quiet"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(completed.returncode == 0, "single-run invocation failed:\n{0}".format(completed.stderr))
        single = json.loads(completed.stdout.strip().splitlines()[-1])
        check(single["determinism"]["runs_compared"] == 1, "--runs was ignored")
        record = load_json(sorted((Path(temp) / "results" / "runs").glob("*.json"))[0])
        check(bool(record["determinism"].get("single_run_caveat")), "a one-run record must carry the single-run caveat")


def check_failure_is_detected(tasks: list) -> None:
    """A suite that cannot fail is not a suite. Break the fixture and confirm."""
    case = load_json(EVAL / "cases" / tasks[0]["fixture"])
    case["retrieval"]["required_chunk_ids"].append("chunk-that-does-not-exist")
    with tempfile.TemporaryDirectory(prefix="ascent-eval-negative-") as temp:
        broken = Path(temp) / "broken-fixture.json"
        broken.write_text(json.dumps(case), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable, str(RUNNER),
                "--runs", "2",
                "--case", str(broken),
                "--results-dir", str(Path(temp) / "results"),
                "--quiet",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(completed.returncode != 0, "the suite passed a fixture it should have failed")
        summary = json.loads(completed.stdout.strip().splitlines()[-1])
        check(summary["outcome"] == "fail", "a broken fixture did not produce a failing outcome")
        check(bool(summary["failed_check_ids"]), "a failing run named no failed check")
        check(bool(summary["failed_task_ids"]), "a failing run named no failed task contract")
        check(
            summary["checks_passed_min"] < summary["checks_total"],
            "a failing run reported every check as passing",
        )


def check_scaffold_generator(profile: dict) -> None:
    with tempfile.TemporaryDirectory(prefix="ascent-eval-scaffold-") as temp:
        output = Path(temp) / "generated"
        command = [
            sys.executable, str(GENERATOR),
            "--profile", str(EVAL / "skill-profile.json"),
            "--output", str(output),
            "--inspect",
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        check(result.returncode == 0, "scaffold generation failed: {0}".format(result.stderr))
        generated_task = json.loads((output / "cases" / "tasks.jsonl").read_text(encoding="utf-8"))
        check(
            generated_task["expected_outcome"] == profile["success_conditions"],
            "scaffold did not preserve success conditions",
        )
        check((output / "inspect" / "README.md").exists(), "Inspect adapter placeholder was not generated")
        repeat = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        check(repeat.returncode != 0, "generator overwrote an existing scaffold")


def check_inspect_poc() -> None:
    poc = (ROOT / "evals" / "inspect-poc" / "context_skill_task.py").read_text(encoding="utf-8")
    dockerfile = (ROOT / "evals" / "inspect-poc" / "Dockerfile").read_text(encoding="utf-8")
    for expected in ("Task", "json_dataset", "react(", "includes()", 'sandbox="docker"'):
        check(expected in poc, "Inspect POC does not map {0}".format(expected))
    check("verify_context_case.py" in dockerfile, "Inspect sandbox omits its verifier")


def check_workbench_cache_policy() -> None:
    spec = importlib.util.spec_from_file_location("evals_workbench_acceptance", WORKBENCH_SERVER)
    check(spec is not None and spec.loader is not None, "cannot load the workbench server")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    server = module.ThreadingHTTPServer(("127.0.0.1", 0), module.WorkbenchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        request = Request(
            "http://127.0.0.1:{0}/evals-workbench.html".format(port),
            headers={"If-Modified-Since": "Fri, 28 Aug 2099 12:00:00 GMT"},
        )
        with urlopen(request) as response:
            check(response.status == 200, "workbench HTML did not load")
            check(
                response.headers.get("Cache-Control") == "no-store",
                "workbench HTML may be cached across branch/server switches",
            )
            body = response.read().decode("utf-8")
            check(
                "Did it work, what did it cost, and how much time did it save?" in body,
                "conditional request reused a stale workbench shell",
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main() -> None:
    profile = load_json(EVAL / "skill-profile.json")
    plan = load_json(EVAL / "eval-plan.json")
    tasks = load_tasks()

    check_metadata(profile, plan, tasks)
    check_stale_paths()
    check_runner(plan, tasks)
    check_failure_is_detected(tasks)
    check_scaffold_generator(profile)
    check_inspect_poc()
    check_workbench_cache_policy()

    print("Passed skill-evaluation acceptance fixtures")


if __name__ == "__main__":
    main()

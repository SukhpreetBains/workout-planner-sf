# Requests for the workbench and telemetry rail

Findings from the evaluation-determinism work that land in files this rail does
not own (`docs/`, `evals/lib/`, `tests/telemetry_acceptance.py`). Written here
rather than edited there, to keep the two changes from colliding.

Ordered by how wrong the output is if nothing changes.

## 1. `docs/evals_workbench.py` reports harness runtime as agent wall-clock

```python
time_block: dict = {"agent_wall_clock_seconds": round(wall_clock, 3)}
baseline = human_baseline()
if baseline:
    time_block["human_baseline_minutes"] = baseline["minutes"]
    time_block["time_saved_minutes"] = round(baseline["minutes"] - wall_clock / 60, 2)
    if wall_clock > 0:
        time_block["speedup_factor"] = round(baseline["minutes"] * 60 / wall_clock, 1)
```

`wall_clock` there is how long the Python subprocess took. There is no agent in
this suite, so there is no agent elapsed time. The line is dormant only because
`baseline/human-baseline.json` currently has `recorded: false`; the moment anyone
records a human baseline, the workbench will publish a `speedup_factor` derived
from machine speed. On this machine the suite takes about two seconds a repeat,
so a four-hour baseline would render as roughly a 7,000x speedup.

**Requested:** set `agent_wall_clock_seconds` to `"not-applicable"` for this
suite with a note, carry the measured figure as `harness_wall_clock_seconds`, and
never compute `time_saved_minutes` or `speedup_factor` from it. The run records
the runner now writes already do this; the simplest fix is item 2.

## 2. The workbench synthesises a run record the runner now writes itself

`run_suite()` builds an `ascent.eval-run-record.v1` from the runner's stdout and
writes it to `results/runs/`. As of this change the runner writes its own
records, one per repeat, to the same directory and with the same
`context-skills-<stamp>-NN` id scheme. Two writers means duplicate records in
one directory and two different answers to the same question, and the
aggregator will average across both.

**Requested:** have the workbench read the paths in the runner's
`run_records` stdout key and display those records, rather than constructing one.
That also fixes item 1, item 3 and gets `determinism`, `hermeticity` and the
per-check detail for free.

The runner's stdout keeps every legacy key the workbench reads today — `suite`,
`outcome`, `evaluated_task_count`, `outcome_pass_rate`, `failed_task_ids`,
`duration_ms` — so nothing breaks before this change is made.

## 3. Two stale assumptions in `run_suite()`

- `checks_total = len(suite_tasks())` equates a check with a task contract. The
  runner now grades seventeen named checks across the four contracts, each with
  its own id and assertion class, and reports both counts separately.
- The comment and the `checks_passed_unavailable_reason` string say "The runner
  aborts at the first failed assertion, so it does not report how many checks
  passed or which one failed." That is no longer true. The runner collects every
  check, counts a check that never executed as a failure, and names each failed
  check id and the reason.

## 4. `consistency_verdict: "insufficient-runs"` is right by accident for this suite

`evals/lib/aggregate.py` returns `insufficient-runs` when
`len(values) < MIN_RUNS_FOR_VERDICT`. For this suite `values` is empty because
every cost field is `"not-applicable"`, which `_numbers()` correctly skips. So
the verdict is accurate in effect — no cost claim is made — but the stated reason
is wrong: there are five runs, not too few. A reader is told to run it more times,
which will never help.

**Requested:** distinguish "no cost data at all" from "too few runs". Something
like `no-cost-data` as a separate verdict value, or an `arm` note when
`len(values) == 0 and len(records) >= MIN_RUNS_FOR_VERDICT`.

Everything else about the aggregator worked first time against the new records:
it reports `correctness_pass_rate: 1.0`, leaves every token, dollar and
wall-clock spread `null`, and returns `deltas: null` with no baseline arm. No
fabricated zeros anywhere. Verified with
`python3 -m evals.lib.aggregate --suite context-skills --runs-dir <dir> --out -`.

## 5. The evaluation contract's telemetry rule changed under you

`skills/design-skill-evals/references/evaluation-contract.md` said "Sum usage
across assistant lines". The redesign spec explicitly retracted that, and the
contract had not caught up. It now says do not sum, deduplicate by `message.id`,
and include subagent sessions with the split reported. It also carries the
inverted Codex cache semantics.

If any part of `evals/lib/telemetry` was written against the old contract text
rather than the spec, it will over-report by 1.76x-2.29x. The handoff says the
harness already deduplicates, so this is probably just a documentation
reconciliation — but it is worth confirming against the code.

## 6. Two blocks worth surfacing in the workbench

Additive to the schema, present in every run record, and the only measured
cross-run facts this suite has:

- `determinism` — `verdict`, `runs_compared`,
  `identical_before_normalisation`, `identical_after_declared_normalisation`,
  `canonical_artifact_sha256`, `declared_volatility` (each with a cause and what
  would close it), and `undeclared_variation`.
- `hermeticity` — workspace, environment, enforced network block, clock pinning,
  hash-seed variation, and the honest note that the suite depends on this
  checkout.

If the workbench shows a headline for this suite, the honest one is "same input,
same output, across five runs" — not anything about cost. Please keep the two
apart on the page: reproducibility of an artifact is not predictability of a
bill.

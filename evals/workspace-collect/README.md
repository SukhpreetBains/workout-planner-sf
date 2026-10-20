# workspace-collect evaluation

Two graders protect scheduled collection.

**`run_deterministic.py`** drives the shipped `collect_inbox.py`, `manage-source-context.py`, and `select_inbox_batch.py` over a synthetic Project and checks what they leave behind:

- only saved sources marked for collection are planned;
- nothing at or before a cursor is collected again;
- each file lands complete, with collection front matter;
- Teams lines carry wall-clock times;
- meeting passcodes and message text stay out of saved state;
- a failed source keeps its cursor.

It also proves the trajectory grader on two synthetic Codex logs, one clean and one containing every forbidden behavior. It then repeats the whole suite, hashes the inbox files, and requires them to match after one declared normalisation: `collected_at`.

```bash
python3 evals/workspace-collect/run_deterministic.py          # 3 runs
python3 evals/workspace-collect/run_deterministic.py --runs 7
```

It needs PyYAML in the interpreter that runs it. The Ascent cached environment has it. The run uses a fresh temporary directory, a temporary `HOME`, `TZ=UTC`, and blocks network APIs in subprocesses.

**`grade_trajectory.py`** grades real scheduled runs from Codex session logs. It reads only turns Codex started on a schedule whose prompt invokes `$workspace-collect`. It fails a turn that:

- runs a `workspace-add` step;
- moves or deletes an inbox file;
- uses a browser, desktop, or screen tool;
- searches Slack or Teams;
- calls a connector tool no contract lists;
- changes the schedule.

A later turn where the user replies **ingest** is expected to run `workspace-add`, so it is never graded. The allowed connector tools come from `workspace-collect/contracts/*.yaml`, so the grader follows the contracts. It also reports tokens per run.

```bash
python3 evals/workspace-collect/grade_trajectory.py --scan ~/.codex/sessions --since 2026-10-20
```

On 2026-10-20 it graded the three real scheduled runs from the end-to-end test. All three passed. Each used 0.84–1.17 million total tokens, 89–96% of them cached input, and about 3,900–4,700 output tokens.

## What this does not answer

- No baseline arm.
- No dollar pricing.
- No human time baseline. None has been recorded, and none is estimated here.
- No harness that launches model runs against stub connectors on demand.
- No grading of the setup conversation's questions.

Each is a named gap in `eval-plan.json`.

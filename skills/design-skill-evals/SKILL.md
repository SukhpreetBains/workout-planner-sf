---
name: design-skill-evals
description: Analyze an Ascent skill or agent harness and generate an evaluation package that answers three questions - did it do the job right, what did it cost and was that predictable, and how much time did it save. Use when creating a skill, turning manual checks or incidents into reusable evaluations, adding cost or consistency measurement to a suite, choosing capability versus regression coverage, selecting graders, or assessing Inspect AI for an evaluation implementation. Do not use for a one-off unit test that needs no skill-level evaluation design.
---

# Design Skill Evals

Produce a reviewable evaluation package that answers three questions about one deliverable:

1. **Did it do the job right?**
2. **What did it cost, and was that predictable?**
3. **How much time did it save?**

Correctness alone is not a product claim. Anyone can get a usable output from an unaided model after hours of prodding and millions of tokens; what Ascent sells is that the same job lands in the same place for a price that can be quoted. A suite that cannot report cost and its spread cannot support that claim.

Write for a consultant, business analyst or delivery lead. Use the plain wording in the contract's glossary; put the standard term in parentheses once. Use deterministic checks by default; add model or human grading only for criteria that code cannot check.

Read [the evaluation contract](references/evaluation-contract.md) before designing or changing a suite — its schemas and glossary are required, not advisory. Read [the Inspect assessment](references/inspect-adoption.md) only when implementing or assessing the optional Inspect adapter.

## 1. Profile the target

Read the target `SKILL.md`, its direct references, scripts, and existing tests. Record only supported behavior. If any required fact is absent, emit `insufficient_information` rather than inventing it.

Capture purpose, supported user intent, inputs, outputs, tools, environment, state boundaries, safety constraints, observable success conditions, trajectory requirements, variable behavior, known failures, and available reference solutions in `skill-profile.json`.

Three additional facts are required, because questions 1 and 3 are unanswerable without them:

- **The deliverable.** What named artifact would a human otherwise produce? Record its kind and whether it is client-facing. A skill whose only output is machine-local state has a thin evaluation by nature — say so rather than dressing it up.
- **The human baseline.** How long does a human take to produce that deliverable, from what record, dated? Ask for a timed manual run or a delivery lead's estimate. If none exists, set `human_baseline.recorded: false` and `minutes: "unknown"`, and carry a `no-human-baseline` gap into the plan. Never estimate it yourself and never derive it from an agent run.
- **The golden reference.** Does a known-good human version of the deliverable exist, and who owns it? If yes, register its `reference_id` and its required section list. If no, record `golden_reference.available: false` with the reason.

Also record `expected_skill_invocations` — the skills a correct run must actually invoke — and `required_clarifying_questions` — what the agent must confirm with the user before producing the deliverable.

Record where the known failure modes came from in `failure_mode_provenance`. Prefer **error analysis** over enumeration: read real traces, open code free-text notes on each, axial code those notes into a failure taxonomy, and count frequencies to decide what to evaluate first. Enumerating failures from the skill contract is an acceptable starting point, but label it `contract-enumeration` — "we guessed these failures from the design; we have not yet watched it fail for real" — and do not present it as observed behavior.

Stop for clarification if the target, deliverable, expected outcome, or safe evaluation environment cannot be identified.

## 2. Select coverage, arms and repeats

Choose one coverage mode and record its rationale:

- **Capability** for a new, difficult, or intentionally low-baseline behavior. For a document deliverable, a capability eval takes the shape of a golden-document comparison.
- **Regression** for a behavior already expected to pass reliably.
- **Hybrid** when a stable core must be protected while new capability is being developed.

Then record both arms in `eval-plan.json`:

- `with-skills` — the Ascent skill library and templates available.
- `baseline-no-skills` — same host, same model, same prompt, same fixture, no Ascent skills or templates.

The reportable result is the delta between them. A single-arm number is not a saving. If the baseline arm cannot be run yet, record `status: "not-implemented"` with the reason and report every delta as `"unknown"`.

Set `runs_per_arm`: the number of whole-suite repeats needed to make a consistency claim. This is not the same as a task's `trials`. Fewer than three runs cannot support a consistency verdict — record `"unknown"`. Five is the working default. Deterministic script suites may keep `runs_per_arm: 1` and record the resulting gap explicitly.

Start with 20–50 representative tasks when a new suite needs breadth; use fewer only when the supported behavior is narrowly deterministic. Derive tasks from requirements, realistic manual checks, known failures, and labeled traces. Use synthetic tasks only to fill named coverage gaps.

For every task, write the user-visible prompt, controlled fixture/environment, observable outcome, `positive`/`negative`/`edge`/`insufficient-information` type, pass and fail conditions, and reference solution when applicable. Make each task passable from its prompt and fixture alone.

Balance "should do" and "should not do" tasks. Do not use textual similarity as the primary quality measure. Keep task data separate from private client material.

Record the `taxonomy` block from the contract's reference axes for classification. It is an appendix-level description of the suite, not the headline.

## 3. Select grading and trials

Grade final environment state or produced artifacts first. Check trajectories only when a required safety, approval, tool-use, or policy behavior makes the path itself part of success.

- Use **code-based** graders for tests, schemas, state, bounds, forbidden data, section presence, and exact policy invariants.
- Use **model-based** graders only for groundedness, claim support, usefulness, completeness, or communication quality that cannot be reduced to code. Give each judge one binary criterion and an `Unknown` result for insufficient evidence.
- Use **human review** to establish intended behavior, calibrate model judges, and resolve a sampled set of ambiguous results.
- Use a **combined** grader only when each component measures a distinct necessary dimension.

Add the two behavioural checks to every agentic suite: did the agent invoke the skills it should have (`skills_invoked` against `skills_expected`), and did it ask the questions it needed to ask (`clarifying_questions_asked` against `clarifying_questions_required`). Both are extracted from the session log by code and reported beside correctness, not folded into the pass rate. A passing artifact produced without invoking the expected skills is evidence about the model, not about the library.

Use one trial for deterministic scripts. For variable behavior, set trials to the smallest number that measures the user-facing reliability requirement and report task success rate and either `pass@k` ("one good attempt is enough") or `pass^k` ("every attempt has to hold"). A guardrail is a `pass^k` requirement: one breach in k attempts is a failure. Isolate every trial and every run from files, caches, credentials, and history left by another.

## 4. Instrument cost and time

Both are extracted by code from the host's session log. No model reads a transcript to produce a metric.

- **Cost.** Input, output, cache-read and cache-creation tokens, total tokens, estimated dollars, turns, tool calls. Report cache reads separately; they price differently. Take per-model rates from one config file with the date they were checked — get current rates from the `claude-api` skill, never hardcode a price inline.
- **Spread.** Across the runs in an arm report min, p50, p95, max, mean and the coefficient of variation ("how much the cost jumps around"), and derive the `consistency_verdict` from the provisional thresholds in the contract. Label the thresholds provisional wherever they are shown.
- **Time.** Agent wall-clock from the first to the last session timestamp, against the recorded human baseline in minutes. Omit `time_saved_minutes` and `speedup_factor` when no baseline is recorded. Never write zero, and never claim a saving against an unsourced number.

Aggregate with the harness, not by hand: `python3 -m evals.lib.aggregate --suite <suite-id>` reads `results/runs/*.json` and writes the `ascent.eval-suite-summary.v1` file at `results/latest.json`.

Every unmeasured field is `"unknown"` and every unanswerable question is a named entry in the plan's `gaps` array, with the specific thing that would close it. Named gaps are the roadmap; guessed values are a liability.

## 5. Generate the scaffold

Generate a framework-neutral package under `evals/<skill-id>/`:

- `README.md` leading with the three questions, then what the suite cannot yet tell you;
- `skill-profile.json` and `eval-plan.json`, including `deliverable`, `human_baseline`, `golden_reference`, `arms`, `runs_per_arm`, `consistency` and `gaps`;
- `cases/tasks.jsonl` with representative task contracts;
- `baseline/human-baseline.json` for the recorded human effort;
- `schemas/` with the run-record and suite-summary example shapes;
- `run_deterministic.py` or an equivalent outcome-grading harness;
- `results/runs/` ignored by Git; and
- an optional `inspect/` adapter when Inspect is justified.

Use `scripts/generate_eval_scaffold.py` to create the initial package. Replace all placeholder assertions, and every `"unknown"` you can legitimately fill, before claiming coverage.

## 6. Validate and maintain

Run every reference solution through the same graders before publishing a task. Test negative cases against the relevant "must not" outcome. Test deterministic graders as ordinary code. Calibrate a model judge against disjoint expert-labeled training, development, and held-out test data before relying on its aggregate score.

Fail a change when correctness drops **or** when cost variance widens. Both are regressions.

Emit a short paste-ready block into the Jira comment or pull request that resolves the work: deliverable, correctness verdict, tokens, estimated cost, agent time, human baseline, time saved, consistency verdict. Facts only, no adjectives, `unknown` where nothing was measured.

Add a task when a production failure, transcript review, or meaningful new capability reveals a new failure mode. Retire or redesign saturated capability tasks only after preserving the corresponding regression behavior.

## Anti-patterns

- Reporting a mean cost with no spread. One number cannot answer "is it 70 credits one time and 40 another?"
- Reporting a with-skills cost with no `baseline-no-skills` arm, so the reader has nothing to compare against.
- Asserting hours saved with no recorded human baseline, or with a baseline derived from the agent's own run.
- Using a model to extract a metric that code can extract, such as re-reading a transcript to count tokens.
- Folding cache-read tokens into input tokens without saying so.
- Computing a consistency verdict from one or two runs.
- Backfilling a plausible-looking number instead of writing `"unknown"` and naming the gap.
- Leading a report with the six-axis taxonomy instead of the three questions.
- Treating a single smoke test as a complete skill evaluation.
- Requiring a single tool-call trajectory when equivalent safe outcomes exist.
- Calling a generic helpfulness judge the primary measure of correctness.
- Reusing a shared workspace, cache, or Git history across trials.
- Treating an uncalibrated model judge as ground truth.

# Project-context skill evaluations

This suite tests the deterministic scripts behind `discover-project-context` and `retrieve-project-context`. It runs in a fresh temporary workspace and touches no real project context or client material.

Read the honest headline first: **this suite answers one of the three questions an Ascent evaluation is supposed to answer.** It checks that the scripts do the right thing. It records nothing about what the workflow costs, how much that cost varies, or how much time it saves — and it has no no-skills comparison to measure any of that against. Those are named gaps in `eval-plan.json`, not omissions.

## What this suite can and cannot tell you

| Question | What it reports today | What is missing |
| -------- | --------------------- | --------------- |
| **1. Did it do the job right?** | Four code checks, pass or fail, on the manifest, the brief, the ranked evidence pack, the access gaps and the cache decision | No known-good human document to compare against, and no proof that a model — rather than the harness — would invoke the right skills or ask the user the questions it needed to ask |
| **2. What did it cost, and was that predictable?** | Nothing | No tokens, no dollars, no spread across repeated runs, and no `baseline-no-skills` arm, so nothing here is a saving |
| **3. How much time did it save?** | Nothing. `duration_ms` is how long the harness took, not a saving | No one has timed a human assembling this evidence pack, so there is no baseline to subtract from |

Why the answer is thin rather than badly written: the deliverable here is machine-local state — a `manifest.json`, a `brief.md` and a ranked evidence pack under `.codex/project-context/`. There is no client-facing document, so there is nothing a human would otherwise have written by hand and nothing to compare against a known-good version. The real evaluation, the one with a golden document and a measurable human baseline, arrives with the skills that turn unstructured content into structured deliverables. That is the argument for staging the work, and it is stated here rather than buried.

## Run

```bash
python3 evals/context-skills/run_deterministic.py
```

Reported metrics: `outcome_pass_rate`, `evaluated_task_count`, `failed_task_ids`, `duration_ms`. Output lands in the Git-ignored `results/`.

The cost and time aggregator is `python3 -m evals.lib.aggregate --suite context-skills`. It reads `ascent.eval-run-record.v1` files from `results/runs/`. This suite does not emit them yet — there is no model session to parse — so the command has nothing to aggregate until an agentic arm exists.

## The four task contracts

Each task in `cases/tasks.jsonl` carries an `intent`, a `graded_surface`, and its `assertion_classes`. Naming the assertion class is what makes coverage legible: a suite with no `forbidden-content` assertion is not testing leakage, whatever its pass rate says.

| Task | Intent | Assertion classes | What a pass proves |
| --- | --- | --- | --- |
| `context-discovery-metadata` | `should-do` | state-verification, schema-validation, forbidden-content | Known source locations are recorded with bounded measurement, the unavailable email source stays a visible access gap, and no source body reaches the manifest or brief |
| `context-unavailable-source` | `must-not` | forbidden-content, tool-call-verification, state-verification | Accessible evidence is usable while the email body stays inaccessible and retrieval does not widen past the recorded sources |
| `context-bounded-retrieval` | `should-do` | relevance-selection, bounds-check, forbidden-content | Required scope, governance and readiness evidence is selected within per-source and total size limits |
| `context-cache-boundary` | `must-not` | freshness-check, relevance-selection, state-verification | A fresh, task-matching cache is reusable, while stale or unrelated entries are rejected |

A `must-not` task is a guardrail, not a task expected to fail: it passes when the forbidden outcome does not occur.

These four are real invariants. They are worth gating a change on. They are not evidence about cost, consistency, or what happens when a model drives the tools.

## Named gaps

Machine-readable in `eval-plan.json` under `gaps`, each with the specific thing that would close it:

| Gap | Plain statement |
| --- | --- |
| `no-cost-data` | No tokens or dollars have been recorded for this suite |
| `no-baseline-arm` | The same job has never been run without the Ascent skills, so nothing here is a saving |
| `consistency-unknown` | How much the cost jumps around is unknown; the suite runs once and measures no tokens |
| `no-human-baseline` | No one has timed a human doing this, so no hours-saved figure can be quoted |
| `no-golden-reference` | There is no known-good human document to compare against |
| `provenance-is-guessed` | We guessed these failures from the design; we have not yet watched it fail for real |
| `behavior-not-observable` | This suite cannot show a model would invoke the right skills or ask the right questions |

A suite whose gaps are named is more useful than a suite whose numbers are guessed.

## The provenance caveat, and what comes before more evals

**Failure-mode provenance is `contract-enumeration`** — we guessed these failures from the design; we have not yet watched it fail for real. The four assertions came from reading the skill contract and the scripts, not from watching real runs go wrong.

The next step is not more tasks. It is error analysis:

1. Collect real traces of the skills in use.
2. **Open code** — write a free-text note on each trace about what actually went wrong.
3. **Axial code** — group those notes into a failure taxonomy.
4. Count the frequencies, and let the counts decide what to evaluate next.

Write evaluators for the failures observed, not the ones imagined at design time. The same loop is already implemented for Agentforce conversations in the `agentforce-error-analysis`, `agentforce-review-interface` and `agentforce-validate-judge` skills; the methodology transfers directly to skill traces.

This is also a regression suite only. No capability tasks, no model-based graders, no repeated agentic trials — so it says nothing about groundedness, completeness, or how the workflow behaves when a model rather than the harness drives the tools.

## Inspect AI: assessed, not adopted

Do not adopt Inspect as a required dependency for these deterministic checks. A local Python runner is simpler to read and to review. The proof of concept in `evals/inspect-poc/` exists to assess Inspect for one genuinely variable, tool-using workflow later; adoption depends on confirming Python compatibility, sandbox availability, model credentials, log retention policy and a host bridge. See [the Inspect assessment](../../skills/design-skill-evals/references/inspect-adoption.md).

## Review and ownership

Review every failure and any new fixture before changing the target skill. The target-skill author owns expected outcomes; a reviewer confirms that a fixture uses no client content and that its reference solution passes.

If this package gains a model-based grader — a second model reading the output and voting — calibrate it before trusting its score: expert labels on disjoint train/dev/test splits, and report how often it agrees with a human about the good ones and about the bad ones (TPR and TNR). An uncalibrated judge is not ground truth. Name one domain expert as the final authority on pass/fail rather than averaging reviewer opinion.

The full requirements this package is measured against are in [the evaluation contract](../../skills/design-skill-evals/references/evaluation-contract.md).

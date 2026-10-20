# Ascent evaluations

Tracked evaluation packages live here. Each package follows the `design-skill-evals` contract and keeps fixtures synthetic or explicitly approved for use. Generated run output belongs in the package-local ignored `results/` directory.

Every package answers three questions, in this order, in these words:

1. **Did it do the job right?** Deterministic checks, comparison against a known-good human document where one exists, and whether the agent invoked the skills and asked the questions it was supposed to.
2. **What did it cost, and was that predictable?** Tokens and dollars per run, and the spread across repeated runs. A mean with no spread is not an answer.
3. **How much time did it save?** Agent elapsed time against a recorded human baseline for the same deliverable.

Questions 2 and 3 are the product claim, not telemetry garnish: correctness alone does not distinguish an Ascent workflow from prodding an unaided model for a few hours. Every headline number is a delta between two arms — `with-skills` and `baseline-no-skills` — and a package that cannot answer one of the three questions records that as a named gap in its `eval-plan.json` rather than backfilling a plausible-looking value.

## The fourth thing every package reports

A package that produces an artifact also reports whether **the same input lands in the same place every time** — the `determinism` block in each run record. Run the whole suite at least three times over one pinned fixture, hash every graded artifact, and compare. Report the raw comparison as well as the normalised one, enumerate every field allowed to vary with its cause and what would close it, and fail the suite on any difference no declared rule explains. Never add a normalisation rule to make a failing comparison pass: that is falsification, not tidying.

This is deliberately kept apart from question 2. Reproducibility of an artifact is not predictability of a bill, and a reader who conflates the two will quote a price off a claim that never mentioned money. A deterministic script suite spends no tokens, so it has no budget excuse for running once — and one run cannot support a reproducibility claim at all.

Each run must also be hermetic, and each run record says what was actually controlled: a fresh temporary workspace, a scrubbed environment with `HOME` redirected, network blocked by *enforcement* rather than by assumption, the clock pinned wherever the target's interface accepts one, and the digest of every script under test carried in the record so a drifted target is visible.

## Marking what is absent

Four markers, and one of them always applies. Getting this wrong is how a plausible-looking number ships.

| Marker | Means |
| ------ | ----- |
| `"unknown"` | We could measure this for this suite and have not |
| `"not-applicable"` | This cannot exist for this suite's design; a sibling `_note` says why |
| `"not-observable"` | Measuring it needs a session log or a user turn this suite does not produce |
| omitted, plus a gap | The schema says to omit it: `human_baseline_minutes`, `time_saved_minutes`, `speedup_factor`, `golden_comparison` |

A gap is never marked closed. When it closes it is deleted and its question moves to `measured`. Reclassifying a gap — "not closable in this suite", "not applicable to this suite" — is not closing it, and a report must say which happened.

Each `eval-plan.json` also carries a `taxonomy` block classifying the suite in the standard vocabulary of AI evaluation practice — eval type, interaction scope, graded surface, grader type, scoring, reliability estimator, execution context, failure-mode provenance, reference dependence — so an engineer can classify a suite without reading its harness. That is a reference classification, not the headline.

Run deterministic packages with their documented Python command, then aggregate cost and time with `python3 -m evals.lib.aggregate --suite <suite-id>`. Agentic packages may additionally include an optional Inspect adapter; they do not make Inspect a dependency of the skill library.

## Packages

| Package | What it answers today |
| ------- | --------------------- |
| [`context-skills`](context-skills/README.md) | Correctness and reproducibility of the project-context scripts. No cost, no time, no baseline arm, and structurally none possible — eight named gaps, none closed |
| [`ascent-initial-setup`](ascent-initial-setup/README.md) | Storage-decision coverage and fresh-workspace readiness, including the missing-identity negative case. No cost, time, baseline, or agent-behavior claims |
| [`workspace-collect`](workspace-collect/README.md) | Collection-script correctness and reproducibility, plus trajectory grading of real scheduled Codex runs (never `workspace-add`, never a browser or search) with tokens per run. No baseline arm, pricing, or human time baseline |
| [`inspect-poc`](inspect-poc/README.md) | An assessment of Inspect AI as an implementation option. Not adopted |

The enforced requirements and the plain-language glossary are in [the evaluation contract](../plugins/ascent/skills/design-skill-evals/references/evaluation-contract.md).

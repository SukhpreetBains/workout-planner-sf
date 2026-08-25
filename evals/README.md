# Ascent evaluations

Tracked evaluation packages live here. Each package follows the `design-skill-evals` contract and keeps fixtures synthetic or explicitly approved for use. Generated run output belongs in the package-local ignored `results/` directory.

Every package answers three questions, in this order, in these words:

1. **Did it do the job right?** Deterministic checks, comparison against a known-good human document where one exists, and whether the agent invoked the skills and asked the questions it was supposed to.
2. **What did it cost, and was that predictable?** Tokens and dollars per run, and the spread across repeated runs. A mean with no spread is not an answer.
3. **How much time did it save?** Agent elapsed time against a recorded human baseline for the same deliverable.

Questions 2 and 3 are the product claim, not telemetry garnish: correctness alone does not distinguish an Ascent workflow from prodding an unaided model for a few hours. Every headline number is a delta between two arms — `with-skills` and `baseline-no-skills` — and a package that cannot answer one of the three questions records that as a named gap in its `eval-plan.json` rather than backfilling a plausible-looking value.

Each `eval-plan.json` also carries a `taxonomy` block classifying the suite in the standard vocabulary of AI evaluation practice — eval type, interaction scope, graded surface, grader type, scoring, reliability estimator, execution context, failure-mode provenance, reference dependence — so an engineer can classify a suite without reading its harness. That is a reference classification, not the headline.

Run deterministic packages with their documented Python command, then aggregate cost and time with `python3 -m evals.lib.aggregate --suite <suite-id>`. Agentic packages may additionally include an optional Inspect adapter; they do not make Inspect a dependency of the skill library.

The enforced requirements and the plain-language glossary are in [the evaluation contract](../skills/design-skill-evals/references/evaluation-contract.md).

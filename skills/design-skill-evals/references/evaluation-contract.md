# Ascent evaluation contract v2

Use this contract for every generated evaluation package. It keeps a suite portable across Claude Code, Codex, Cursor, Copilot and a framework-specific adapter.

The reader of an Ascent evaluation is a consultant, business analyst or delivery lead deciding whether to trust and fund an agentic workflow. Write for that reader: lead with the plain question, put the standard term in parentheses once, and keep the borrowed taxonomy in the [reference section](#reference-the-borrowed-classification-axes) at the end. The [glossary](#plain-language-glossary) is the required wording.

## The three questions

Every package answers all three, in this order, in these words.

| # | The question a reader asks | What is measured | Required block |
| - | -------------------------- | ---------------- | -------------- |
| 1 | **Did it do the job right?** | Deterministic checks, how close the output came to a known-good human document, and whether the agent used the skills and asked the questions it was supposed to | `correctness`, `behavior` |
| 2 | **What did it cost, and was that predictable?** | Tokens and dollars per run, and the spread across repeated runs | `cost` |
| 3 | **How much time did it save?** | Agent wall-clock against a recorded human baseline for the same deliverable | `time` |

Correctness on its own does not support the product claim. Anyone can get a usable output from an unaided model after hours of prodding and several million tokens. What Ascent sells is that the same job lands in the same place, for a price that can be quoted. So cost and consistency are evaluation outcomes, not telemetry decoration.

Question 2 has two halves and both are required. A cheap average with a wide spread is a worse product than a slightly dearer run that lands in the same place every time. **Report the spread, not just the mean.**

A package that cannot answer one of the three questions records that as a named gap in `eval-plan.json` (see [Marking what is unknown](#marking-what-is-unknown)). It does not omit the block and it does not fill it with a plausible-looking number.

## Both arms, always

Every headline claim is a delta, never an absolute. Each suite runs the same task under two arms:

| `arm` | What is available | What it establishes |
| ----- | ----------------- | ------------------- |
| `with-skills` | The Ascent skill library, templates and reference documents | The product |
| `baseline-no-skills` | Same host, same model, same prompt, same fixture, no Ascent skills or templates | "Just throwing it into Claude" |

Only the skill library differs between arms. Same host, model, prompt, fixture and grader, or the delta measures the wrong thing.

The reportable result is the difference: tokens saved, minutes saved, and whether the baseline arm reached a passing output at all. Without the baseline arm, "it cost 40,000 tokens" tells a delivery lead nothing.

If the baseline arm is not implemented, record it as `status: "not-implemented"` in the plan's `arms` block with the reason, and report every delta as `"unknown"`. Do not report a with-skills figure as if it were a saving.

## Question 1 — Did it do the job right?

Three kinds of check, in this order of preference.

### 1. Deterministic checks

Code-based assertions on the final state or artifact: schema validation, state verification, bounds, forbidden content, executable tests. Each check names its `assertion_classes` (see [Task records](#task-records)) so a coverage gap is visible on the page: a suite with no `forbidden-content` assertion is not testing leakage, whatever its pass rate says.

### 2. Golden-document comparison

This is the shape a capability eval takes when the deliverable is a document. Compare the agent's output against a known-good human document — a real deliverable from a real engagement, approved for evaluation use — and report structure and support, not textual similarity.

```json
"golden_comparison": {
  "reference_id": "mobilize-raid-log-2025",
  "required_sections_present": 8,
  "required_sections_total": 9,
  "missing_sections": ["Escalation path"],
  "unsupported_claims": 0,
  "verdict": "partial"
}
```

Rules:

1. `reference_id` points at a registered reference document with a recorded owner and approval. A comparison against an agent-generated "golden" document is not a golden comparison.
2. Section presence is a code check against the reference's section list. Never a model call.
3. `unsupported_claims` counts statements in the output that no cited source supports. This is the one part of the comparison a model judge may perform, as a single binary criterion per claim, returning `Pass`, `Fail` or `Unknown` with the evidence retained.
4. `verdict` is `pass`, `partial` or `fail`. `partial` never counts as a pass in a release gate.
5. Do not use textual or embedding similarity to the reference as the quality measure. A reworded correct document is correct; a fluent document missing the escalation path is not.
6. Omit `golden_comparison` entirely when the suite has no reference document, and record `golden_reference.available: false` with the reason in the profile.

### 3. Behavioural checks

Two checks, both named as required by the stakeholder review, both extracted from the session log by code:

- **Did the agent invoke the skills it should have?** `skills_invoked` against `skills_expected`, with `missing_skill_invocations` listed. A passing artifact produced without invoking the expected skills is still a finding: the artifact did not come from the library, so it is not evidence about the library.
- **Did the agent ask the user the questions it needed to ask?** `clarifying_questions_asked` against `clarifying_questions_required`. A workflow that guesses a project root instead of confirming it can produce a correct-looking document from the wrong inputs.

Both live in the run record's `behavior` block. Both are reported alongside correctness, never folded into the pass rate silently.

## Question 2 — What did it cost, and was that predictable?

Per run, report input tokens, output tokens, cache-read tokens, cache-creation tokens, total tokens, estimated dollars, turns and tool calls. Across runs in an arm, report min, p50, p95, max, mean and the coefficient of variation ("how much the cost jumps around").

### What a skill run costs

Measure a specific skill by isolation: one run is one fresh agent session with
one target skill workflow, one controlled prompt and fixture, and one graded
deliverable. Attribute the whole session to that run, including later turns,
tool calls and subagents caused by the workflow. This is the figure labelled
"credits per run" or "tokens per run."

Do not assign tokens to the `Skill` tool's own round trip. Loading instructions
usually takes a fraction of a second; the work they direct happens later and is
not bracketed by that tool result. Per-skill-call duration is diagnostic timing,
not skill-run cost.

When one session invokes several skills as an end-to-end Ascent process, report
the total as **workflow cost** and list the skills invoked. Do not manufacture a
per-skill split from timestamps or nearby model requests. To compare individual
skill costs, run each target workflow in its own isolated session as a separate
suite or task, then compare those complete run records.

Rules:

1. **Never report a mean without a spread.** One number with no spread cannot answer "is it 70 credits one time and 40 credits another time?"
2. Cache reads are reported separately from input tokens and priced separately. Folding them into one total without saying so makes a cache-heavy session look far more expensive than it is.
3. Dollar figures come from one config file holding per-model rates with the date they were checked. Get current rates from the `claude-api` skill. Never hardcode a price inline, and never print a dollar figure whose rate date is not recorded.

### Consistency verdict

Derived from the coefficient of variation of `total_tokens` across the runs in an arm.

| CV | Verdict | Plain reading |
| -- | ------- | ------------- |
| < 0.10 | `predictable` | Cost per run is safe to quote to a client |
| 0.10–0.30 | `variable` | Budget with headroom; investigate the spread |
| > 0.30 | `unpredictable` | Do not quote a per-run cost; the workflow is not stable |

**These thresholds are provisional.** They are a recorded starting position so they can be argued with, not a validated standard. Label them provisional wherever they are displayed.

A consistency verdict needs repetition to mean anything. Fewer than three runs in an arm gives `consistency_verdict: "unknown"`; do not compute a CV from one or two runs. Five runs per arm is the working default.

### Telemetry extraction rules

**Deterministic only.** Parse the logs with code. No model reads a session transcript to produce a metric — that is both expensive and unverifiable.

Sources, both confirmed present:

- **Claude Code** — `~/.claude/projects/<path-slug>/<session-uuid>.jsonl`, one JSON object per line. `type: "assistant"` lines carry `message.usage` with `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, and `message.model`. Every line carries `timestamp`. Tool calls appear as `tool_use` content blocks. Take wall-clock from the first to the last timestamp.

  **Do not sum usage across assistant lines.** An earlier version of this contract said to, and it was wrong. Claude Code writes one assistant message as several JSONL lines, one per content block, and repeats the *same* `message.usage` object on every one of them. Measured on this repo's own sessions: 105 assistant lines collapse to 61 real messages, and in all 37 cases where an id spans multiple lines the usage block is byte-identical. Naive summation inflates totals by 1.76x-2.29x. Deduplicate by `message.id`, falling back to `requestId` then `uuid`, collect content blocks across all lines of a message, and deduplicate tool calls by `tool_use` id.

  **Subagent sessions are separate files and they dominate the bill.** They live at `<session-uuid>/subagents/agent-*.jsonl` with a `.meta.json` beside them. On one real session, main-thread-only reported $3.65 against $23.19 including subagents — a 7.3x understatement. Include them by default and always report the split.
- **Codex** — `~/.codex/sessions`. Its token semantics are *inverted* from Claude Code's: `cached_input_tokens` is a **subset** of `input_tokens` rather than an addition to it, and `reasoning_output_tokens` is likewise a subset of `output_tokens`, so a naive cross-host field mapping double-counts cache reads. Codex wall-clock is unreliable on resumed threads — one real rollout carries 12 session starts and spans 6.8 days — so flag it rather than trust it when multiple session starts appear. If a host's shape cannot be confirmed, record the adapter as unimplemented rather than guessing.

Aggregation is a code path, not a prompt: `python3 -m evals.lib.aggregate --suite <suite-id>` reads the run records and writes the suite summary.

### Reproducibility is not the same claim as cost consistency

A suite that produces an artifact can also report whether the *same input produces the same output*. Report it in the run record's `determinism` block, and keep it strictly separate from the cost `consistency_verdict`. One is about the artifact, the other about the bill; a reader who conflates them will quote a price off a claim that never mentioned money.

Rules for a reproducibility claim:

1. **One run proves nothing.** Run the whole suite at least three times over the same pinned input and compare. A single run reports `runs_compared: 1` and carries a caveat saying so.
2. **Compare the artifacts, not the log.** Hash every graded artifact, walk the output directory rather than listing files by name, and report the digest. A stable digest is a drift fingerprint; a changed one is a diff to read, not a number to update.
3. **Report the raw comparison too.** If the raw artifacts differ, say so, and do not present the normalised result as though nothing varied.
4. **Enumerate every normalisation rule** with what it masks, the cause, and what would close it. A difference no declared rule explains **fails the suite** and is reported with its file and the differing line.
5. **Never add a rule to silence a regression.** A rule declares a field legitimately volatile. Adding one to make a red suite green is falsification.
6. **Vary the incidental, pin the material.** Vary `PYTHONHASHSEED` across runs so set-ordering non-determinism surfaces; pin the fixture, the clock where the interface allows it, and the environment.

### Hermeticity

A reproducibility claim is worthless if the run quietly depends on the machine. Record what was actually controlled in the run record's `hermeticity` block, and say plainly what was not:

- a fresh temporary workspace per run, removed afterwards;
- a scrubbed environment with `HOME` redirected to a throwaway directory, so no dotfile or developer setting reaches the target;
- network blocked and **enforced** rather than assumed — an injected `sitecustomize.py` that raises on socket use is enforcement; a sentence in a README is not;
- the clock pinned wherever the target's interface accepts one, with the residue declared;
- inputs pinned and hashed, including the digest of every script under test, so a drifted target is visible in the record.

## Question 3 — How much time did it save?

Report the agent's wall-clock in seconds and the human baseline in minutes for the **same deliverable**.

Rules:

1. `human_baseline_minutes` must come from a human record — a delivery lead's estimate, a timesheet, or a timed manual run — and carry `human_baseline_source` with the method and date.
2. When no baseline has been recorded, omit `human_baseline_minutes`, `time_saved_minutes` and `speedup_factor`. Do not write zero. Record the gap `no-human-baseline` in the plan.
3. Never derive a human baseline from the agent's own run, from a model's guess, or from a comparable-sounding task. An unsourced "saves 4 hours" is the vague eight-points-to-five-points claim this contract exists to replace.
4. Agent wall-clock is elapsed time from the first to the last session timestamp, including tool time and the user's own turnaround. Do not net out waiting; the reader is comparing against a human's elapsed hours.

## Required files

```
evals/<suite-id>/
  README.md              three questions first, then what this suite cannot tell you
  skill-profile.json     ascent.skill-eval-profile.v1
  eval-plan.json         ascent.skill-eval-plan.v1
  cases/tasks.jsonl      one task contract per line
  baseline/              recorded human effort for the deliverable
  results/runs/          one ascent.eval-run-record.v1 per run, Git-ignored
  results/latest.json    ascent.eval-suite-summary.v1, Git-ignored
  schemas/               machine-readable key contracts, validated by the harness and the tests
```

## Schema: run record

One file per run at `evals/<suite-id>/results/runs/<run-id>.json`. Example shape; values are illustrative, not measured.

```json
{
  "schema_version": "ascent.eval-run-record.v1",
  "run_id": "context-skills-20260821T140312Z-01",
  "suite_id": "context-skills",
  "arm": "with-skills",
  "started_at": "2026-08-21T14:03:12Z",
  "ended_at": "2026-08-21T14:05:48Z",
  "host": { "name": "claude-code", "version": "…", "model": "claude-opus-5" },

  "correctness": {
    "outcome": "pass",
    "checks_total": 4,
    "checks_passed": 4,
    "failed_check_ids": [],
    "golden_comparison": {
      "reference_id": "mobilize-raid-log-2025",
      "required_sections_present": 8,
      "required_sections_total": 9,
      "missing_sections": ["Escalation path"],
      "unsupported_claims": 0,
      "verdict": "partial"
    }
  },

  "cost": {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read_tokens": 0,
    "cache_creation_tokens": 0,
    "total_tokens": 0,
    "estimated_usd": 0.0,
    "turns": 0,
    "tool_calls": 0
  },

  "time": {
    "agent_wall_clock_seconds": 156,
    "human_baseline_minutes": 240,
    "human_baseline_source": "delivery-lead-estimate · 2026-08-21 · Mobilize RAID log",
    "time_saved_minutes": 237,
    "speedup_factor": 92.3
  },

  "behavior": {
    "skills_invoked": ["discover-project-context", "retrieve-project-context"],
    "skills_expected": ["discover-project-context", "retrieve-project-context"],
    "missing_skill_invocations": [],
    "clarifying_questions_asked": 2,
    "clarifying_questions_required": ["confirm project root", "confirm phase"]
  },

  "provenance": {
    "telemetry_source": "claude-code-session-jsonl",
    "session_path": "~/.claude/projects/<slug>/<uuid>.jsonl",
    "extraction": "deterministic"
  }
}
```

Required: `schema_version`, `run_id`, `suite_id`, `arm`, `started_at`, `ended_at`, `host`, `correctness`, `cost`, `time`, `behavior`, `provenance`.

- `arm` is `with-skills` or `baseline-no-skills`. There is no third value and no default.
- `golden_comparison` is omitted when the suite has no reference document.
- `human_baseline_minutes` is omitted when no baseline has been recorded — never invented, never derived from the agent's own run.
- `provenance.extraction` must be `deterministic`. A metric extracted any other way does not belong in a run record.

## Schema: suite summary

One file per suite at `evals/<suite-id>/results/latest.json`, aggregating k runs per arm. Written only by `python3 -m evals.lib.aggregate --suite <suite-id>`.

```json
{
  "schema_version": "ascent.eval-suite-summary.v1",
  "suite_id": "context-skills",
  "generated_at": "2026-08-21T14:20:00Z",
  "runs_per_arm": 5,
  "arms": {
    "with-skills": {
      "correctness_pass_rate": 1.0,
      "total_tokens": { "min": 0, "p50": 0, "p95": 0, "max": 0, "mean": 0,
                        "coefficient_of_variation": 0.0 },
      "estimated_usd": { "min": 0.0, "p50": 0.0, "max": 0.0 },
      "wall_clock_seconds": { "min": 0, "p50": 0, "max": 0,
                              "coefficient_of_variation": 0.0 },
      "consistency_verdict": "predictable"
    },
    "baseline-no-skills": { "…": "same shape" }
  },
  "deltas": {
    "tokens_saved_p50": 0,
    "usd_saved_p50": 0.0,
    "minutes_saved_p50": 0,
    "correctness_pass_rate_delta": 0.0,
    "consistency_improvement": "…"
  }
}
```

Every `deltas` value is `"unknown"` when the corresponding arm or baseline is missing. An arm with fewer than three runs reports `consistency_verdict: "unknown"`.

## Schema: profile

```json
{
  "schema_version": "ascent.skill-eval-profile.v1",
  "skill_id": "example-skill",
  "purpose": "Supported user outcome.",
  "deliverable": {
    "name": "Named artifact a human would otherwise produce",
    "kind": "document | structured-artifact | machine-local-state",
    "client_facing": true,
    "path_or_form": "Where the deliverable lands"
  },
  "human_baseline": {
    "recorded": false,
    "minutes": "unknown",
    "source": "unknown",
    "note": "How it will be recorded, or why it cannot be."
  },
  "golden_reference": {
    "available": false,
    "reference_id": null,
    "owner": null,
    "note": "Why no known-good human document exists for this deliverable."
  },
  "expected_skill_invocations": ["skill-id"],
  "required_clarifying_questions": ["What the agent must confirm before producing the deliverable"],
  "interfaces": {
    "inputs": ["User request", "Declared local artifacts"],
    "outputs": ["Named deliverable"],
    "tools": ["Optional connector or script"],
    "environment": ["Required state and isolation boundary"]
  },
  "success_conditions": ["Observable final state or artifact property"],
  "trajectory_requirements": ["Only policy, safety, or approval requirements"],
  "known_failure_modes": [],
  "failure_mode_provenance": "contract-enumeration",
  "unknowns": []
}
```

`deliverable`, `human_baseline` and `golden_reference` are required. They are what make questions 1 and 3 answerable: without a named deliverable there is nothing to compare, and without a recorded human baseline there is no time saving to claim.

`unknowns` must contain every required fact that cannot be supported by the target skill. A generated task with a non-empty blocking unknown has `case_type: "insufficient-information"` and is not scored as agent failure.

`failure_mode_provenance` is required. `contract-enumeration` means "we guessed these failures from the design; we have not yet watched it fail for real." Say that, rather than implying the taxonomy came from observed traces.

## Schema: evaluation plan

```json
{
  "schema_version": "ascent.skill-eval-plan.v1",
  "skill_id": "example-skill",
  "questions": {
    "correctness": {"status": "measured", "how": "code-based assertions plus golden comparison"},
    "cost": {"status": "not-instrumented", "how": "unknown"},
    "time": {"status": "not-instrumented", "how": "unknown"}
  },
  "arms": {
    "with-skills": {"status": "implemented", "note": "Ascent skills and templates available."},
    "baseline-no-skills": {"status": "not-implemented", "note": "Reason, and what it would take."}
  },
  "runs_per_arm": 5,
  "consistency": {
    "metric": "coefficient_of_variation(total_tokens)",
    "verdict": "unknown",
    "thresholds": {"predictable": "< 0.10", "variable": "0.10-0.30", "unpredictable": "> 0.30"},
    "thresholds_status": "provisional"
  },
  "coverage": {"mode": "hybrid", "rationale": "Stable safety behavior plus a new capability."},
  "trials": {"count": 1, "reliability_metric": "outcome_pass_rate", "rationale": "Deterministic scripts."},
  "graders": [{"id": "outcome", "type": "code", "required": true, "rationale": "Artifact is objectively checkable."}],
  "metrics": ["correctness_pass_rate", "total_tokens", "estimated_usd", "wall_clock_seconds", "time_saved_minutes", "consistency_verdict"],
  "gaps": [
    {"id": "no-human-baseline", "question": "time", "statement": "No human effort has been recorded for this deliverable.", "unblocked_by": "One timed manual run or a delivery-lead estimate with a date."}
  ],
  "aggregation": {"command": "python3 -m evals.lib.aggregate --suite example-skill"},
  "taxonomy": {"…": "reference classification, see the appendix"},
  "transcript_review": {"sample": "all failures and grader disagreements"}
}
```

`questions`, `arms`, `runs_per_arm`, `consistency`, `metrics` and `gaps` are required. `coverage.mode` and `taxonomy.eval_type` must agree.

`runs_per_arm` is the number of whole-suite repeats needed to support a consistency claim, which is a different thing from a task's `trials`. `trials` is per-task reliability under one run; `runs_per_arm` is cost and time reproducibility across runs.

Use `capability` coverage for deliberately challenging tasks with headroom, `regression` for expected-reliable behavior, and `hybrid` when both are needed. A capability task graduates only after it is reliably solved and its task remains representative.

## Task records

Store one JSON object per line in `cases/tasks.jsonl`:

```json
{
  "id": "example-positive-01",
  "case_type": "positive",
  "intent": "should-do",
  "prompt": "User-visible task with all required details.",
  "fixture": "fixtures/example-positive",
  "expected_outcome": ["Observable state or artifact condition"],
  "must_not": ["Forbidden state, content, or side effect"],
  "graded_surface": ["outcome"],
  "assertion_classes": ["state-verification", "forbidden-content"],
  "scoring": "binary",
  "reference_solution": "Reference artifact path or null when not applicable",
  "graders": ["outcome"],
  "trials": 1
}
```

Use `negative` when a behavior must not occur and `edge` for an intentionally difficult but solvable boundary. Use `insufficient-information` when a task cannot be made passable without missing facts; record the missing facts and exclude it from rate calculations.

`intent` states the plain reading of the case: `should-do` for a behavior the skill must produce, `must-not` for a guardrail that must hold. A `must-not` case is not expected to fail — it passes when the forbidden outcome does not occur.

`assertion_classes` names what each code-based check actually asserts, drawn from: `exact-match`, `regex-match`, `schema-validation`, `state-verification`, `bounds-check`, `forbidden-content`, `executable-test`, `static-analysis`, `tool-call-verification`, `relevance-selection`, `freshness-check`, `section-presence`, `claim-support`.

## Marking what is unknown

Never backfill a plausible-looking value. Four mechanisms, and one of them always applies:

1. The literal string `"unknown"` in a scalar field that *could* be measured for this suite but has not been.
2. The literal string `"not-applicable"` in a field that **cannot exist** for this suite's design, or `"not-observable"` in one that would need a session log or a user turn the suite does not produce. Both must carry a sibling field ending in `_note` stating why. These are distinct from `"unknown"`: "we did not measure the tokens" and "there is no model, so there are no tokens" are different facts, and collapsing them into one word reads as unfinished work rather than a structural limit.
3. Omission plus a gap, for the fields the run-record schema says to omit (`human_baseline_minutes`, `time_saved_minutes`, `speedup_factor`, `golden_comparison`).
4. An entry in the plan's `gaps` array: `id`, which `question` it blocks, a `status`, a one-sentence `statement` in plain language, and `unblocked_by` — the specific thing that would close it.

A gap's `status` distinguishes `open` from `open-and-not-closable-in-this-suite` and `not-applicable-to-this-suite`. A gap is never marked "closed": when it closes, it is deleted and the corresponding question moves to `measured`. Reclassifying a gap is not closing it, and a report must say which happened.

A suite whose gaps are named is more useful than a suite whose numbers are guessed. The gaps are the roadmap.

## Grading rules

1. Prefer a state, artifact, test, parser, schema, security or bounds check.
2. Extract every metric with code. If code can extract it, a model must not. A model that reads a transcript to count tokens is both expensive and unauditable.
3. Add partial dimensions only when they identify distinct useful failures; preserve a binary release gate where a safety or required outcome demands it.
4. Use a model judge only for a named, non-objective criterion — claim support, groundedness, communication quality. Request `Pass`, `Fail` or `Unknown` and retain the evidence for its result.
5. Calibrate model judges with expert labels on disjoint train/dev/test splits. Report true-positive and true-negative rates, not raw accuracy alone.
6. Record trajectory and behavioural checks separately from correctness. Do not make them release gates unless the checked path is expressly required behavior.
7. Run every trial and every run in a clean environment. Do not expose reference answers, previous transcripts, caches or Git history that a production user would not have.
8. Name one domain expert as the final authority on pass/fail rather than averaging reviewer opinion.

## Emitting the result into the workflow

The metric has to land where the work is tracked, not only in a report. The harness emits a short paste-ready block for a Jira comment or PR body: deliverable, correctness verdict, tokens, estimated cost, agent time, human baseline, time saved, consistency verdict. Facts only, no adjectives. Every unmeasured field says `unknown` rather than being dropped, so a reader can see what was not measured.

## Where these evaluations run

Both, staged:

1. **Now — internal drift detection.** The team owns the skill library. The suite runs when a skill, template or prompt changes, and it fails the change if correctness drops or cost variance widens.
2. **Later — external self-validation.** Once the library ships beyond the team, the same suite goes with it, so anyone modifying a skill can prove their change still produces a passing, affordably-priced output.

Same harness, two audiences. Design for the second one now: no dependency on a local checkout, on private client material, or on anyone's personal machine paths.

## Error analysis before more evals

A suite labelled `contract-enumeration` has not yet been through error analysis, and more enumerated tasks will not fix that. The next step is not more evals; it is reading what actually went wrong:

1. Collect real traces of the skill in use.
2. **Open code** — write a free-text note on each trace about what went wrong.
3. **Axial code** — group those notes into a failure taxonomy.
4. Count frequencies, and let the counts decide what to evaluate next.

Write evaluators for the failures actually observed, not the ones imagined at design time. The same loop is implemented for Agentforce conversations in the `agentforce-error-analysis`, `agentforce-review-interface` and `agentforce-validate-judge` skills; the methodology transfers directly to skill traces.

## Plain-language glossary

Required wording. The standard term may appear once, in parentheses, after the plain phrasing.

| Standard term | Say this instead |
| ------------- | ---------------- |
| `pass^k` | every attempt has to hold |
| `pass@k` | one good attempt is enough |
| coefficient of variation | how much the cost jumps around |
| `contract-enumeration` | we guessed these failures from the design; we have not yet watched it fail for real |
| `error-analysis` provenance | we read real traces of it going wrong and tested what we found |
| `arm: baseline-no-skills` | the same job with no Ascent skills — just throwing it into Claude |
| golden reference / reference-based | compared against a known-good human document |
| reference-free | graded with no known-good answer to compare against |
| outcome verification | we checked what it produced |
| trajectory analysis | we checked the path it took, not just what it produced |
| `"unknown"` | we could measure this and have not |
| `"not-applicable"` | this cannot exist for this suite — say why in the same breath |
| `"not-observable"` | measuring this would need a session log or a user turn this suite does not produce |
| reproducibility / `determinism` | the same input lands in the same place every time |
| declared volatility | the short list of fields we know vary, why, and what would stop them |
| hermeticity | the run does not depend on whose machine it ran on |
| `capability` eval | can it do the hard new thing yet |
| `regression` eval | does the thing that already worked still work |
| `single-trial` | we ran it once |
| `insufficient-information` case | the task cannot be passed as written; facts are missing |
| LLM-as-Judge / model-based grader | a second model reads the output and votes |
| TPR / TNR | how often the judge agrees with a human about the good ones and about the bad ones |
| eval saturation | the test got too easy to tell anything apart |
| p50 | the middle run |
| p95 | the bad run, short of the worst |
| `consistency_verdict: predictable` | cost per run is safe to quote |
| `consistency_verdict: variable` | budget with headroom |
| `consistency_verdict: unpredictable` | do not quote a per-run cost yet |

Two further rules from the review:

- Cut any diagram that does not change a decision.
- Cut invented rationale. If a reason was not actually the reason, delete it.

<a id="shared-vocabulary"></a>

## Reference: the borrowed classification axes

This is the vocabulary an AI engineer uses to classify a suite on sight. It is accurate and it stays, but it is not the frame a delivery lead reads. Keep it in an appendix; lead with the three questions.

Sources: [Anthropic, *Demystifying evals for AI agents*](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (A) and [Hamel Husain, *Evals FAQ* / `ai-evals-course/evals-skills`](https://hamel.dev/blog/posts/evals-faq/) (H).

| Axis | Values | Meaning | Source |
| --- | --- | --- | --- |
| **Eval type** | `capability`, `regression`, `hybrid` | Capability evals target new or hard behavior and are expected to have headroom. Regression evals protect behavior that already works. | A |
| **Interaction scope** | `single-turn`, `multi-turn`, `agentic` | Agentic evals let the model plan, call tools, and take many steps in an environment. | A |
| **Graded surface** | `outcome`, `trajectory` | Outcome verification grades final state or produced artifacts. Trajectory (transcript / tool-call) analysis grades the path taken. | A |
| **Grader type** | `code-based`, `model-based`, `human` | Code-based graders are assertions: exact/regex match, schema validation, static analysis, executable tests, bounds, forbidden content. Model-based graders are LLM-as-Judge. Human graders are SME review and spot-check sampling. | A, H |
| **Scoring** | `binary`, `partial-credit`, `weighted`, `hybrid` | Prefer binary pass/fail. Likert scales invite a subjective middle default and slow annotation. | A, H |
| **Reliability estimator** | `single-trial`, `pass@k`, `pass^k` | `pass@k` when one successful attempt is sufficient. `pass^k` when every repeated attempt must succeed — the correct estimator for a guardrail. | A |
| **Judge calibration** | `TPR`, `TNR`, `bias-corrected success rate` | Report true-positive and true-negative rates against expert labels on disjoint train/dev/test splits. Never raw accuracy alone. | H |
| **Execution context** | `ci-offline`, `production-monitoring`, `guardrail` | CI suites are small and favor cheap deterministic assertions. Production monitoring samples live traces with reference-free judges and confidence intervals. Guardrails run inline and synchronously in the request path. | H |
| **Failure-mode provenance** | `contract-enumeration`, `error-analysis`, `incident` | Error analysis is the preferred origin: read traces, **open code** free-text notes, **axial code** them into a **failure taxonomy**, then build evaluators for the failures actually observed. | H |
| **Reference dependence** | `reference-based`, `reference-free` | Reference-based grading compares against a known-correct answer. Reference-free grading judges quality in absolute terms; required in production where no reference exists. | H |

Two further terms are load-bearing:

- **Eval saturation** — a capability eval whose pass rate has reached ceiling no longer discriminates. Monitor for it and retire or redesign the task while preserving the corresponding regression behavior. (A)
- **Benevolent dictator** — one named domain expert is the final authority on quality standards, so annotation disagreements resolve instead of averaging out. (H)

A `taxonomy` block using these values stays required in every `eval-plan.json`, so a reader can classify a suite without reading its harness. It is a classification, not a report of results.

## What changed in v2

v1 measured correctness only, and led with the axes above. v2 makes cost and consistency first-class, requires the baseline arm, requires the run-record and suite-summary schemas, and demotes the axes to this appendix. The `ascent.skill-eval-profile.v1` and `ascent.skill-eval-plan.v1` schema ids are unchanged — v2 adds required blocks inside them rather than renaming the schemas, because tooling in this repository already reads them by those ids.

# SGAF-717 · Evaluation redesign spec

Working spec. Every subagent working on the evaluation redesign reads this
first and treats the schemas and vocabulary below as fixed. Source of the
requirements: the 2026-08-21 "Ascent Evals Discussion" between Andrew Fischer,
Calvin O'Keefe and Gada Lam.

## Why this redesign exists

The first evaluation suite was correct and useless. Andrew, in the review:
"These evals make sense, like I understand what they're doing, but it doesn't
help us at all. I'm trying to imagine a business analyst running this
evaluation and doing anything with the output."

The suite measured one thing (did the scripts behave) in borrowed academic
vocabulary, for an audience of AI engineers. The people who need to read it are
consultants, business analysts and delivery leads deciding whether to trust and
fund an agentic workflow.

Calvin named the fix. There are three questions, not one:

> "To build this deck, we used this many tokens and it took this long. Those are
> two of the important metrics, and the third one is, and it did the right thing.
> If we can validate those three things somehow, I feel like that is our test
> suite, or that's our sales pitch. There's an overlap between the two."

And the reason the third question is not enough on its own:

> "What makes what we're building different than just throwing it into Claude?
> Which you probably can get Claude to give you the output you want after a few
> hours of prodding and poking it, and after several millions of tokens. The
> real value of what we're building is consistency and cost savings."

So: consistency and cost savings are not nice-to-have telemetry. They are the
product claim. An evaluation that does not measure them cannot support it.

## The three questions

These replace the six-axis taxonomy as the primary frame. Every deck, workbench
and README leads with these, in this order, in these words.

| # | The question a reader asks | What we measure | Metric block |
| - | -------------------------- | --------------- | ------------ |
| 1 | **Did it do the job right?** | Deterministic checks, plus how close the output came to a known-good human document | `correctness` |
| 2 | **What did it cost, and was that predictable?** | Tokens and dollars per run, and the spread across repeated runs | `cost` |
| 3 | **How much time did it save?** | Agent wall-clock against a recorded human baseline for the same deliverable | `time` |

Question 2 has two halves and both are required. A cheap average with a wide
spread is a worse product than a slightly dearer run that lands in the same
place every time, because consistency is what we are selling. Report the spread,
not just the mean.

## The comparison arm

Every headline claim is a delta, never an absolute. Each suite runs the same
task twice:

- `arm: "with-skills"` — the Ascent skill library and templates available.
- `arm: "baseline-no-skills"` — the same host and model, same prompt, no Ascent
  skills or templates. This is Calvin's "just throwing it into Claude."

The reportable result is the difference: tokens saved, minutes saved, and
whether the baseline arm even reached a passing output. Without the baseline
arm, "it cost 40,000 tokens" means nothing to a delivery lead.

## Schema: run record

One file per run, at `evals/<suite-id>/results/runs/<run-id>.json`.

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
    "input_tokens": 18244,
    "output_tokens": 5310,
    "cache_read_tokens": 1349247,
    "cache_creation_tokens": 62880,
    "total_tokens": 1435681,
    "reasoning_output_tokens": null,
    "estimated_usd": 1.03,
    "turns": 12,
    "tool_calls": 47,
    "model_requests": 61,
    "context_window": 1000000,
    "peak_context_utilization": 0.49,
    "credits": null,
    "credits_unavailable_reason": "Credits are the Codex billing unit. This run was on Claude Code, which is billed in dollars."
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

`golden_comparison` is omitted when the suite has no reference document.
`human_baseline_minutes` is omitted when no baseline has been recorded — never
invent one, and never derive it from the agent's own run.

**The figures above are an illustration, not a template.** An earlier version of
this example carried `0` in every token field and `0.0` in `estimated_usd`, which
contradicted this document's own rule two sections down that `estimated_usd` is
nullable and that a zero is a false cost claim rather than a missing one. Those
literal zeros were being copied verbatim into the packages the scaffold generator
produced. A field that has not been measured is `null` with a reason recorded
beside it, or absent from the document entirely. It is never `0`.

Three fields carry that rule explicitly:

- `reasoning_output_tokens` is a **subset** of `output_tokens` on Codex and
  `null` on Claude Code, which does not report it. `null` means "this host does
  not report the figure", not "no reasoning happened", and it is never added to
  `output_tokens`.
- `credits` is `null` on any host not billed in credits, with
  `credits_unavailable_reason` saying which. It is a **derived** figure —
  measured tokens times a published rate card — so wherever it is displayed it
  carries the rate card's source and fetch date.
- `agent_wall_clock_seconds` is `"not-applicable"` for a suite with no model in
  the loop. A harness runtime belongs in `harness_wall_clock_seconds`, and
  `time_saved_minutes` and `speedup_factor` are never derived from it: pairing a
  two-second script with a four-hour human baseline publishes a 7,000x speedup.

## Schema: suite summary

One file per suite at `evals/<suite-id>/results/latest.json`, aggregating k runs
per arm.

```json
{
  "schema_version": "ascent.eval-suite-summary.v1",
  "suite_id": "context-skills",
  "generated_at": "2026-08-21T14:20:00Z",
  "runs_per_arm": 5,
  "arms": {
    "with-skills": {
      "runs": 5,
      "correctness_pass_rate": 1.0,
      "total_tokens": { "min": 402118, "p50": 431905, "p95": 486330,
                        "max": 491284, "mean": 438291,
                        "coefficient_of_variation": 0.082 },
      "estimated_usd": { "min": 0.29, "p50": 0.31, "max": 0.35 },
      "credits": null,
      "credits_unavailable_reason": "No run in this arm was billed in credits.",
      "wall_clock_seconds": { "min": 141, "p50": 156, "max": 179,
                              "coefficient_of_variation": 0.094 },
      "consistency_verdict": "predictable"
    },
    "baseline-no-skills": { "…": "same shape" }
  },
  "deltas": {
    "tokens_saved_p50": 1264883,
    "usd_saved_p50": 0.94,
    "credits_saved_p50": null,
    "minutes_saved_p50": 38,
    "correctness_pass_rate_delta": 0.6,
    "consistency_improvement": "…"
  }
}
```

The same rule applies here. A spread block whose underlying series is empty
carries `null` in every position, not `0`, and the arm records why — a run count
below the verdict threshold is `insufficient-runs`, whereas an arm with enough
runs and no cost telemetry at all is `no-cost-data`. The two want opposite advice
from the reader: the first says run it again, and the second says running it
again will never help.

### Consistency verdict

Derived from the coefficient of variation of `total_tokens` across runs in an
arm. This is the direct answer to Calvin's "is it 70 credits one time and 40
credits another time?"

| CV | Verdict | Plain reading |
| -- | ------- | ------------- |
| < 0.10 | `predictable` | Cost per run is safe to quote to a client |
| 0.10–0.30 | `variable` | Budget with headroom; investigate the spread |
| > 0.30 | `unpredictable` | Do not quote a per-run cost; the workflow is not stable |

Thresholds are a starting position, recorded so they can be argued with. Label
them as provisional wherever they are displayed.

## Telemetry extraction rules

**Deterministic only.** Calvin's constraint, and the reason his own first
attempt was expensive: "without doing it non-deterministically and having it go
re-review every section and re-input every token plus all of the tool token
information." Parse the logs with code. No model reads a session transcript to
produce a metric.

Sources, both confirmed present:

- **Claude Code** — `~/.claude/projects/<path-slug>/<session-uuid>.jsonl`. One
  JSON object per line. `type: "assistant"` lines carry `message.usage` with
  `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
  `cache_creation_input_tokens` and `message.model`. Every line carries
  `timestamp`. Tool calls appear as `tool_use` content blocks. Take wall-clock
  from the first to the last timestamp.

  **Do not sum usage across assistant lines.** An earlier version of this spec
  said to, and it was wrong. Claude Code splits one assistant message across
  several JSONL lines, one per content block, and *every one of those lines
  repeats the same `message.usage` object*. Measured on this repo's own
  sessions: 105 assistant lines collapse to 61 real messages, and in all 37
  cases where an id spans multiple lines the usage block is byte-identical.
  Naive summation inflates totals by 1.76x-2.29x. Deduplicate by `message.id`,
  falling back to `requestId` then `uuid`, and collect content blocks across all
  lines of a message, deduplicating tool calls by `tool_use` id.

  **Subagent sessions are separate files and they dominate the bill.** They live
  at `<session-uuid>/subagents/agent-*.jsonl` with a `.meta.json` beside them.
  On the session that produced this redesign, main-thread-only reported $3.65
  against $23.19 including subagents - understating by 7.3x. Include them by
  default and always report the split: a fan-out architecture is exactly the
  thing whose cost a reader needs to see.
- **Codex** — `~/.codex/sessions`. Implemented and verified against real
  rollouts. Its token semantics are *inverted* from Claude Code's:
  `cached_input_tokens` is a **subset** of `input_tokens`, not an addition to it
  (verified: 16,184 + 144 = 16,328 total, with 4,864 cached *inside* the
  16,184), and `reasoning_output_tokens` is likewise a subset of
  `output_tokens`. Mapping these fields across hosts naively double-counts cache
  reads. Codex wall-clock is unreliable on resumed threads - one real rollout
  carries 12 `session_meta` lines and spans 6.8 days - so flag it rather than
  trust it when multiple session starts appear.

Cache reads are reported separately from input tokens and are priced separately.
Do not fold them into a single total without saying so — cache-heavy sessions
otherwise look far more expensive than they are.

For dollar figures: get current per-model rates from the `claude-api` skill.
Keep them in one config file with the date they were checked. Never hardcode a
price inline.

`estimated_usd` is **nullable and must stay nullable**. A Codex run on a
non-Anthropic model has no applicable Anthropic rate; emitting `0.0` there is a
false cost claim rather than a missing one. Cache-write TTL is not recoverable
from the aggregate `cache_creation_input_tokens` field, so 5-minute versus
1-hour write pricing is a declared assumption that must be surfaced next to any
figure derived from it.

Environment note: this machine has Python 3.9.6 only. The harness is written to
3.9-compatible syntax despite the 3.10+ target named earlier in this spec.

## Where these evaluations run

Calvin left this open: "Is it something that we, the admins of the system, run
to make sure that there's not too much drift over time? Or is it a thing that is
used given out once this goes external, so that when you make modifications you
can still validate that it works? I'm not really sure."

The recorded answer is **both, staged**:

1. **Now — internal drift detection.** The team owns the skill library. The
   suite runs when a skill, template or prompt changes, and it fails the change
   if correctness drops or cost variance widens.
2. **Later — external self-validation.** Once the library ships beyond the team,
   the same suite goes with it, so anyone modifying a skill can prove their
   change still produces a passing, affordably-priced output.

Same harness, two audiences. Design for the second one now: no dependency on a
local checkout, on private client material, or on anyone's personal machine
paths.

## Emitting the result into the workflow

The metric must land where work is tracked, not only in a report. Calvin:

> "I think one of the outputs from whatever we're building here, in the
> resolution of the JIRA story or in the pull request that the agent makes, it
> puts in some metric around hours saved versus doing it manually. Instead of it
> just being some vague, like, oh, it feels like it took an 8 point story to a
> 5 point story."

So the harness emits a short, paste-ready block — deliverable, correctness
verdict, tokens, cost, agent time, human baseline, time saved, consistency
verdict — suitable for a Jira comment or PR body. Facts only, no adjectives.

## Language rules

The reader is a consultant or business analyst, not an AI engineer.

- Lead with the plain question. The standard term goes in parentheses after it,
  once, or in an appendix.
- `pass^k` → "every attempt has to hold." `pass@k` → "one good attempt is
  enough." `coefficient of variation` → "how much the cost jumps around."
  `contract-enumeration` → "we guessed these failures from the design; we have
  not yet watched it fail for real."
- Cut any diagram that does not change a decision. Andrew on the current deck:
  "really just went overboard with all of these visualizations."
- Cut invented rationale. Andrew on the current deck: "these are AI slop reasons
  for why we did things." If a reason was not actually the reason, delete it.
- Keep the honest-limitation content. The project-context skills are
  deterministic shell scripts with no client-facing deliverable, so their
  evaluation is thin by nature. Both participants agreed the real evaluation
  arrives with the skills that turn unstructured content into structured
  documents. That is the argument for the staged plan, not something to bury.

## Retained from the current work

Do not delete these. Demote them to a reference appendix, keep them accurate.

- The six-axis taxonomy and the borrowed vocabulary, with sources.
- The four existing task contracts and their assertion classes.
- The error-analysis-before-more-evals argument and the honest
  `contract-enumeration` provenance label.
- The Inspect assessment and its "do not adopt yet" recommendation.

## Addenda — questions raised during implementation

### Correctness of a non-deterministic baseline arm

The comparison arm's headline is not "did the baseline pass" but "how often did
it pass." `correctness_pass_rate` already exists per arm in the suite summary;
use it. A baseline arm that produces an acceptable document twice in five
attempts reports `0.4`, and that is exactly the finding worth showing — an
unaided model reaching the answer sometimes, at higher cost, is the honest
version of the comparison. Never collapse it to a pass/fail.

Consistency verdicts stay defined over cost only. Correctness reliability is the
pass rate; do not overload one word with both.

### Required-section lists for a golden comparison

`required_sections_total` comes from the **deliverable template in the skill
library**, not from the reference document. The template is the contract the
skill is trying to satisfy; the reference document is evidence a human satisfied
it. Deriving the section list from the reference would make each comparison
unfalsifiable against its own answer key. Record the template path in
`golden_comparison.section_source`.

### Emitting the block

For now the harness writes the block to stdout and to
`results/<run-id>-summary.md`, for manual paste. Do not build a Jira transition
hook: no authenticated Jira connector was available during this work, and the
existing `git-workflow` and `jira-workflow` skills already own that surface.
Wiring it to a PR body is a later, separate change.

### Open — needs a decision, do not guess

- **Golden reference sourcing.** Real approved client deliverables are the only
  meaningful reference, but the staged plan ships this suite outside the team,
  and private client material cannot travel with it. These requirements
  conflict. Until it is resolved, treat golden fixtures as redacted or
  synthesised structural stand-ins, and never commit a client artifact.
- **Run budget.** Five runs across two arms per changed skill is a recurring
  token bill nobody has sized, which is a poor look for a suite whose thesis is
  cost discipline. Provisional policy, to be confirmed: a single `with-skills`
  run per change, and the full two-arm repeat set only per deliverable type on a
  deliberate cadence. Record which policy a suite follows in `eval-plan.json`.

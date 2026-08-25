# SGAF-717 evaluation handoff

Status: working branch `feature/sgaf-717-skill-evals`. Not POC-ready, per the
2026-08-21 review. Consolidated on one branch deliberately; open the PR when
there is a 0.1 worth reviewing.

## What changed, and why

The first version of this work was correct and unusable. It measured one thing —
did the scripts behave — in vocabulary borrowed from AI-evaluation research, for
an audience of AI engineers. The people who have to read it are consultants,
business analysts and delivery leads.

The verdict that triggered the rewrite, from the author in the review: "These
evals make sense, like I understand what they're doing, but it doesn't help us at
all. I'm trying to imagine a business analyst running this evaluation and doing
anything with the output."

Calvin supplied the replacement frame. There are three questions, not one:

1. **Did it do the job right?**
2. **What did it cost, and was that predictable?**
3. **How much time did it save?**

His reasoning for why correctness alone proves nothing: "What makes what we're
building different than just throwing it into Claude? Which you probably can get
Claude to give you the output you want after a few hours of prodding and poking
it, and after several millions of tokens. The real value of what we're building
is consistency and cost savings."

So cost and its spread are not telemetry garnish. They are the product claim, and
an evaluation that cannot report them cannot support it. Everything below follows
from that.

The full requirement set, traced to the conversation, is in
[`sgaf-717-evals-redesign-spec.md`](sgaf-717-evals-redesign-spec.md).

## What was built

| Area | Location | Summary |
| --- | --- | --- |
| Redesign spec | [`docs/sgaf-717-evals-redesign-spec.md`](sgaf-717-evals-redesign-spec.md) | The three questions, both run schemas, the comparison arms, consistency thresholds, extraction rules, language rules. The fixed contract this work was built against. |
| Cost and time harness | `evals/lib/` | Deterministic session-log parsers for Claude Code and Codex, dated pricing config, k-run aggregator with cost variance, paste-ready summary emitter. Standard library only. |
| Evaluation contract v2 | [`skills/design-skill-evals/references/evaluation-contract.md`](../skills/design-skill-evals/references/evaluation-contract.md) | Restructured around the three questions. Both run schemas required. Taxonomy demoted to a reference appendix, attributions intact. Plain-language glossary. |
| Evaluation-design skill | [`skills/design-skill-evals/SKILL.md`](../skills/design-skill-evals/SKILL.md) | Six steps. Profiling now requires the deliverable, the human baseline and whether a golden reference exists. Anti-patterns grew from 5 to 13. |
| Project-context suite | [`evals/context-skills/`](../evals/context-skills/) | Four task contracts unchanged. Metadata rewritten to record honestly what is *not* measured, with seven named gaps. |
| Presentation | [`docs/sgaf-717-evals-presentation.html`](sgaf-717-evals-presentation.html) | 16 slides. Opens on the three questions; taxonomy in an appendix. |
| Workbench | [`docs/evals-workbench.html`](evals-workbench.html), [`docs/evals_workbench.py`](evals_workbench.py) | Three headline results, per-run cost spread, arm-vs-arm deltas, copy-paste summary block, honest empty states. |

## Two corrections to how agent cost is measured

Both were found by building the harness against real logs. Both would have made
every cost figure wrong, in the same direction: too high, then too low.

**Do not sum token usage across assistant log lines.** Claude Code writes one
assistant message as several JSONL lines, one per content block, and repeats the
*same* `message.usage` object on every one. Verified on this repo's own sessions:
105 assistant lines collapse to 61 real messages, and in all 37 cases where a
message id spans multiple lines the usage block is byte-identical. Naive
summation inflates totals by 1.76x-2.29x. The harness deduplicates by
`message.id`. Two independent implementations agree to the token: 6,435,922.

**Subagents are separate files and they dominate the bill.** On session
`8ef5b54d`, main-thread-only reported $3.65 against $23.19 including subagents —
a 7.3x understatement. Any cost claim that ignores fan-out is fiction, and
fan-out is how this redesign was built.

Codex needs its own care: `cached_input_tokens` is a **subset** of
`input_tokens`, inverted from Claude Code's semantics, so a naive cross-host
mapping double-counts cache reads.

## Known limits of the harness

Recorded because a metric nobody trusts is worse than no metric.

- **Subagent discovery is incomplete.** It finds `<session-uuid>/subagents/agent-*.jsonl`.
  The session that produced this redesign wrote no such files, so its four
  subagents — roughly 942,000 self-reported tokens — are invisible to the
  harness, and `--subagents` and `--no-subagents` return identical figures. Until
  this is closed, treat any single-session cost as a floor, not a total.
- **Skill detection has false positives.** It sees the `Skill` tool and Bash paths
  into `skills/<name>/`, and cannot distinguish reading a skill file from
  executing one. On this session it reported three skills that were only ever
  mentioned in text. A skill auto-loaded by a hook leaves no trace at all.
- **Question counting** is exact for `AskUserQuestion` and a heuristic upper bound
  otherwise. Codex has no equivalent, so its count is heuristic-only.
- **Cache-write TTL is not recoverable** from the aggregate field, so 5-minute
  versus 1-hour write pricing is a declared assumption, surfaced beside the
  figure.
- **Codex wall-clock is unreliable on resumed threads.** One real rollout carries
  12 session starts and spans 6.8 days. Flagged rather than trusted.

## What this suite can and cannot tell you

The honest answer is one of three questions, and that is structural rather than
unfinished.

| Question | Status |
| --- | --- |
| Did it do the job right? | **Measured.** Four code-based task contracts, 4/4 passing. |
| What did it cost, and was that predictable? | **Not instrumented, and not instrumentable here.** The suite runs local Python scripts. There is no model, so there is no session log, so there are no tokens. |
| How much time did it save? | **Not instrumented.** No human has been timed assembling this evidence pack, and a baseline must never be derived from an agent's own run. |

There is also no `baseline-no-skills` arm, because there is no meaningful
"without the skills" version of a shell script.

This is the finding that matters most, and it confirms where the review landed.
The project-context skills are plumbing: deterministic scripts producing
machine-local state, with no client-facing deliverable. Renaming every label will
not make their evaluation interesting, because two of the three questions cannot
be asked of them.

Calvin, in the review: "I think this will work better when we actually get to the
part where we're taking unstructured content and turning it into structured
documents on the other side or structured microsites on the other side. I feel
like then we'll have a very specific input-output to test against."

## Recommendation for the 0.1

Do not put this branch forward as the POC. Build one more suite first, against a
single document-producing skill — a RAID log or a Risk Gate brief — where all
three questions are answerable at once:

- a real deliverable to compare against a known-good human version;
- a real session log to price, including subagents;
- a real human baseline to beat.

That is the suite a delivery lead can read and act on, and it is the one that
demonstrates consistency and cost savings rather than asserting them.

## Open decisions

These need a human ruling and were deliberately not guessed.

1. **Golden reference sourcing.** Real approved client deliverables are the only
   meaningful reference, but the staged plan ships this suite outside the team and
   private client material cannot travel with it. These requirements conflict.
   Until resolved, golden fixtures stay redacted or synthesised structural
   stand-ins, and no client artifact is committed.
2. **Run budget.** Five runs across two arms per changed skill is a recurring
   token bill nobody has sized — a poor look for a suite whose thesis is cost
   discipline. Provisional: one `with-skills` run per change, full two-arm repeat
   sets per deliverable type on a deliberate cadence.
3. **The consistency thresholds are invented.** Under 0.10 "safe to quote a
   per-run cost", 0.10–0.30 variable, over 0.30 unpredictable. They are labelled
   provisional everywhere they appear, but they are the kind of number that
   hardens into fact once it is on a slide. Decide what evidence is required
   before any per-run cost is quoted externally.
4. **First real signal is unflattering.** Aggregating three real sessions gave a
   cost coefficient of variation of **0.86** — `unpredictable`, far past the
   provisional 0.30 band. Those were ad-hoc development sessions, not controlled
   eval runs, so it is not a fair measurement of a skill workflow. It is,
   however, the first real evidence on Calvin's exact question, and it points the
   wrong way. Worth knowing before quoting a price to anyone.

## Where these evaluations run

Calvin left this open: admin-run drift detection, or shipped to external users so
they can validate their own modifications? The recorded answer is **both,
staged** — internal drift detection now, external self-validation once the
library ships beyond the team. Same harness, two audiences; design for the second
one now, which means no dependency on a local checkout, private client material,
or anyone's machine paths.

## Emitting the result into the workflow

Calvin: "one of the outputs ... in the resolution of the JIRA story or in the pull
request that the agent makes, it puts in some metric around hours saved versus
doing it manually. Instead of it just being some vague, like, oh, it feels like it
took an 8 point story to a 5 point story."

The harness emits a paste-ready facts block to stdout and to
`results/<run-id>-summary.md`, and the workbench has a copy button for it. No Jira
transition hook was built: no authenticated Jira connector was available, and the
existing `git-workflow` and `jira-workflow` skills already own that surface.

## Run and review

```bash
python3 evals/context-skills/run_deterministic.py            # correctness only
python3 -m evals.lib.telemetry --session <path> --out <f>    # cost and time from a session log
python3 -m evals.lib.aggregate --suite context-skills        # k runs, spread, arm deltas
python3 -m evals.lib.emit_summary --suite context-skills     # the paste-ready block
python3 docs/evals_workbench.py --port 8765                  # then open evals-workbench.html
```

Tests: `tests/skill_evals_acceptance.py`, `tests/telemetry_acceptance.py`,
`tests/context_skills_acceptance.py`, `tests/validate_context_skills.py`. All
four pass on this branch.

The workbench keeps its execution boundary: one allowlisted suite, the browser
chooses no command, model, path or fixture, a fresh temporary workspace per run
under a 90-second timeout, and Git-ignored results.

## Sources

Vocabulary is borrowed on purpose, and now lives in an appendix rather than the
opening. [Anthropic, *Demystifying evals for AI
agents*](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
for the classification axes. [Hamel Husain, *Evals
FAQ*](https://hamel.dev/blog/posts/evals-faq/) and
[ai-evals-course/evals-skills](https://github.com/ai-evals-course/evals-skills)
for the method: error analysis first, open and axial coding, the failure
taxonomy, binary over Likert, judge validation by TPR and TNR, the single quality
authority. [Inspect AI](https://inspect.aisi.org.uk/) as one optional
implementation — assessed, still not adopted as a dependency.

Error analysis remains the next methodological step, and it has not been done.
The four assertions were derived from the skill contract, which the profile
records as `contract-enumeration`: we guessed these failures from the design; we
have not yet watched it fail for real.

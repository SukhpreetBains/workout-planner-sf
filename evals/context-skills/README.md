# Project-context skill evaluations

This suite tests the deterministic scripts behind `discover-project-context` and `retrieve-project-context`. It runs in a fresh temporary workspace and touches no real project context or client material.

Read the honest headline first: **this suite answers one of the three questions an Ascent evaluation is supposed to answer, plus one more it added for itself.** It checks that the scripts do the right thing, and it proves the output is reproducible run to run. It records nothing about what the workflow costs, how much that cost varies, or how much time it saves — and it has no no-skills comparison to measure any of that against. Those are named gaps in `eval-plan.json`, not omissions.

## What this suite can and cannot tell you

| Question | What it reports today | What is missing |
| -------- | --------------------- | --------------- |
| **1. Did it do the job right?** | A registry of named code checks, each with its own id and assertion class, graded against four task contracts on the manifest, brief, ranked evidence, access gaps and cache decision | No known-good human document to compare against, and no proof that a model — rather than the harness — would invoke the right skills or ask the user the questions it needed to ask |
| **2. What did it cost, and was that predictable?** | Nothing, and nothing is possible here | No tokens, no dollars, no spread, and no `baseline-no-skills` arm, so nothing here is a saving |
| **3. How much time did it save?** | Nothing. `harness_wall_clock_seconds` is machine speed, not a saving | No one has timed a human assembling this evidence pack, so there is no baseline to subtract from |
| **Also measured: does it land in the same place every time?** | Yes. The suite repeats the whole pipeline, hashes every graded artifact and compares the runs | Two timestamp-derived fields still vary. They are declared, not hidden — see below |

Why the answer to questions 2 and 3 is thin rather than badly written: the deliverable here is machine-local state — a `manifest.json`, a `brief.md` and a ranked evidence pack under `workspace/.system/project-context/`. There is no client-facing document, so there is nothing a human would otherwise have written by hand and nothing to compare against a known-good version. The real evaluation, the one with a golden document and a measurable human baseline, arrives with the skills that turn unstructured content into structured deliverables. That is the argument for staging the work, and it is stated here rather than buried.

## Run

```bash
python3 evals/context-skills/run_deterministic.py               # runs_per_arm repeats, read from eval-plan.json
python3 evals/context-skills/run_deterministic.py --runs 7       # more repeats
python3 evals/context-skills/run_deterministic.py --quiet        # JSON summary only
```

Each repeat writes one `ascent.eval-run-record.v1` file to the Git-ignored `results/runs/`. The runner validates every record it writes against `schemas/run-record.contract.json` and fails the suite if one violates it, so a schema drift cannot ship quietly.

The cost and time aggregator is `python3 -m evals.lib.aggregate --suite context-skills`. It now has records to read. It will report the correctness pass rate and leave every token, dollar and wall-clock figure `null`, because those fields carry the marker `not-applicable` and the aggregator does not coerce a marker to zero. That is the correct output, not a bug.

## Reproducibility: what is proven, and what still varies

A determinism suite that runs once proves nothing, so this one does not run once. Every invocation runs the whole pipeline `runs_per_arm` times over the same pinned fixture, each in its own temporary workspace, and hashes every graded artifact. Runs are compared against the first, both raw and after a short, enumerated normalisation ruleset.

- **Raw artifacts are not identical, and the run record says so.** `identical_before_normalisation` is `false`.
- **After the declared rules, they are byte-identical.** `identical_after_declared_normalisation` is `true` and every run reports the same `canonical_artifact_sha256`. That digest is a drift fingerprint: change a target script's output and it changes.
- **Anything the declared rules cannot explain fails the suite** and is reported with its file and the differing line, under `undeclared_variation`. Nothing is quietly normalised away.

The two declared sources of variation:

| Rule | What varies | Why | What would close it |
| ---- | ----------- | --- | ------------------- |
| `iso8601-utc-timestamp` | Every timestamp in the manifest, brief, index, per-source summaries and state file | `project_context.py` and `persist_context.py` call `datetime.now(timezone.utc)` and accept no clock argument | An optional `--now` on both scripts, matching the one `cache_context.py` already accepts |
| `state-manifest-digest` | `state.json`'s `manifest_sha256` | It is a digest over a manifest containing the timestamps above, so it inherits their volatility | The same injectable clock |

**This is reproducibility of the output, not consistency of cost.** It says the same input produces the same artifacts. It says nothing about tokens or dollars, which this suite cannot measure. Do not present it as an answer to "what did it cost, and was that predictable?"

## Hermeticity

Recorded in every run record under `hermeticity`, because a claim about reproducibility is worthless if the run quietly depends on the machine it ran on.

- **Fresh temporary workspace** per repeat, removed afterwards.
- **Scrubbed environment.** The inherited shell environment is discarded; only `PATH`, `HOME`, `TMPDIR`, `LC_ALL`, `LANG`, `TZ` and `PYTHON*` are set. `HOME` points at a throwaway directory, so a script reading a dotfile would find an empty home rather than the developer's.
- **Network blocked and enforced, not assumed.** A `sitecustomize.py` on `PYTHONPATH` raises on socket construction, `create_connection`, `socketpair`, `getaddrinfo` and `gethostbyname` in every subprocess. A new network call fails the run instead of succeeding quietly.
- **Clock pinned where the interface allows.** Cache decisions are taken against the recorded retrieval timestamp plus a fixed offset declared in the fixture, so `age_hours` is an exact number rather than a reading of the developer's clock. What remains is the declared volatility above.
- **Hash seed varied, not pinned.** `PYTHONHASHSEED` differs per repeat. Pinning it would mask set-ordering non-determinism, which is exactly the class of bug worth catching.
- **Inputs pinned and hashed.** Every run record carries the sha256 of the case fixture and of all four target scripts.
- **It does depend on this checkout**, inherently: the suite executes the skill scripts from the library it ships inside. That is not a dependency on any particular machine — the harness counts the absolute-path substitutions it had to make before hashing, and the count is zero.

## The four task contracts

Each task in `cases/tasks.jsonl` carries an `intent`, a `graded_surface`, and its `assertion_classes`. Naming the assertion class is what makes coverage legible: a suite with no `forbidden-content` assertion is not testing leakage, whatever its pass rate says. Each contract is graded by several named checks, and the run record lists every one with its own outcome — so a failure names the check that failed rather than reporting a bare pass rate.

| Task | Intent | Assertion classes | What a pass proves |
| --- | --- | --- | --- |
| `context-discovery-metadata` | `should-do` | state-verification, schema-validation, forbidden-content | Known source locations are recorded with bounded measurement, the unavailable email source stays a visible access gap, and no source body reaches the manifest or brief |
| `context-unavailable-source` | `must-not` | forbidden-content, tool-call-verification, state-verification | Accessible evidence is usable while the email body stays inaccessible and retrieval does not widen past the recorded sources |
| `context-bounded-retrieval` | `should-do` | relevance-selection, bounds-check, forbidden-content | Required scope, governance and readiness evidence is selected within per-source and total size limits, and low-signal and restricted chunks are excluded |
| `context-cache-boundary` | `must-not` | freshness-check, relevance-selection, state-verification | A fresh, task-matching cache is reusable, while stale or unrelated entries are rejected |

A `must-not` task is a guardrail, not a task expected to fail: it passes when the forbidden outcome does not occur.

A check that never executed — because an earlier step in its phase raised — is recorded as a failure, not dropped from the denominator. `checks_passed` over `checks_total` is therefore honest even on a crash.

These contracts are real invariants. They are worth gating a change on. They are not evidence about cost, about consistency of cost, or about what happens when a model drives the tools.

## Named gaps

Machine-readable in `eval-plan.json` under `gaps`, each with a status and the specific thing that would close it. **None of them is closed by the reproducibility work.** Two are reclassified, because "not implemented yet" was the wrong description of them.

| Gap | Status | Plain statement |
| --- | --- | --- |
| `no-cost-data` | not closable here | No tokens or dollars have been recorded, and none can be: there is no model, so there is no session log |
| `no-baseline-arm` | not applicable here | There is no no-skills version of a shell script. Removing the Ascent skills removes the subject of the test rather than establishing a control |
| `consistency-unknown` | open, partly addressed | How much the cost jumps around is still unknown. The suite no longer runs once, but it measures no tokens |
| `no-human-baseline` | open | No one has timed a human doing this, so no hours-saved figure can be quoted |
| `no-golden-reference` | open | There is no known-good human document to compare against |
| `provenance-is-guessed` | open | We guessed these failures from the design; we have not yet watched it fail for real |
| `behavior-not-observable` | open | This suite cannot show a model would invoke the right skills or ask the right questions |
| `clock-not-injectable` | open | The graded artifacts are not byte-identical in raw form, because two target scripts stamp the current time into them and take no clock argument |

`clock-not-injectable` is new. It was found by building the reproducibility check rather than assumed at design time, and it is recorded rather than absorbed into the normalisation and forgotten.

A suite whose gaps are named is more useful than a suite whose numbers are guessed.

## The provenance caveat, and what comes before more evals

**Failure-mode provenance is `contract-enumeration`** — we guessed these failures from the design; we have not yet watched it fail for real. The assertions came from reading the skill contract and the scripts, not from watching real runs go wrong.

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

Two review rules specific to this suite:

- **A changed `canonical_artifact_sha256` is a diff to read, not a number to update.** It means a target script's output changed. Establish that the change was intended before accepting it.
- **Never add a normalisation rule to make a failing comparison pass.** A rule is a declaration that a field is legitimately volatile, with a stated cause and a route to closing it. Adding one to silence a real regression is the exact dishonesty this suite exists to prevent.

If this package gains a model-based grader — a second model reading the output and voting — calibrate it before trusting its score: expert labels on disjoint train/dev/test splits, and report how often it agrees with a human about the good ones and about the bad ones (TPR and TNR). An uncalibrated judge is not ground truth. Name one domain expert as the final authority on pass/fail rather than averaging reviewer opinion.

The full requirements this package is measured against are in [the evaluation contract](../../skills/design-skill-evals/references/evaluation-contract.md).

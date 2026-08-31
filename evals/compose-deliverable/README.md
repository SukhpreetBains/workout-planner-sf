# Compose-deliverable evaluations

Deliverable under evaluation: **Editable executive-readout PowerPoint deck from approved content**.

1. **Did it do the job right?** The runner builds the pinned synthetic shared-content fixture, checks independently declared source text and section coverage in the native PPTX, runs the structural validator, and exercises its deliberately broken deck cases.
2. **What did it cost, and was that predictable?** Unknown. This deterministic runner has no model session. It does not treat browser or build duration as a token cost.
3. **How much time did it save?** Unknown. No human baseline or agent session duration has been recorded.

The source fixture is the same structured content boundary that a companion microsite would use. This suite deliberately does not scrape the microsite DOM: the skill contract names the shared content artifact as the source of truth.

## Run

```bash
python3 evals/compose-deliverable/run_deterministic.py
python3 -m evals.lib.aggregate --suite compose-deliverable
```

The second command is available after the `feature/skill-evals` PR merges. To demonstrate tokens and a savings delta, run the fixture through a model in both `with-skills` and `baseline-no-skills` arms and let the eval telemetry harness parse the session logs.

## Current gaps

- No model-session token, cost, or agent-time record exists.
- The no-skills baseline arm is not implemented.
- No human time baseline exists.
- No approved human deck is registered as a golden reference.
- Skill invocation and clarifying-question behavior are not observable in this script-driven run.

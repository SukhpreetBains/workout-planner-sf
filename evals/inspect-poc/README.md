# Inspect proof of concept

This proof of concept maps an Ascent generated evaluation scaffold to an Inspect `Task`, JSON `Dataset`, ReAct-agent `Solver`, outcome `Scorer`, Docker `Sandbox`, and Inspect log viewer. It deliberately uses a synthetic context-skill fixture and no client data.

## Prerequisites

- Python version supported by the selected `inspect-ai` release.
- A current `inspect-ai` package available through the approved package source.
- Docker running locally.
- Credentials for the selected model provider.

## Run

From this directory:

```bash
python3 -m pip install inspect-ai
inspect eval context_skill_task.py --model <provider/model>
inspect view
```

The agent receives a bounded challenge, operates only in the Docker sandbox, and passes when it returns `CONTEXT_EVAL_PASS`. The sandboxed verifier checks the fixture’s required evidence and prevents the restricted email sentinel from appearing in its generated evidence output.

## Interpretation

This is a working shape validation, not a production agent-host bridge. A production adapter must substitute the target skill’s real fixtures, implement its harness connection and tool policy, preserve logs safely, and replace the sentinel scorer with task-specific outcome checks. See `skills/design-skill-evals/references/inspect-adoption.md` for the adoption recommendation and constraints.

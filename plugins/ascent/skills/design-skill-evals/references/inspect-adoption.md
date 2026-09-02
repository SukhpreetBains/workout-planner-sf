# Inspect AI assessment

## POC mapping

| Generated scaffold | Inspect concept | POC choice |
| --- | --- | --- |
| `cases/tasks.jsonl` | Dataset / `Sample` | JSON dataset with task prompt and success sentinel |
| skill profile + task | `Task` | `context_skill_agent_eval()` |
| target agent harness | Solver / `react()` agent | ReAct with `bash()` and `todo_write()` |
| outcome assertion | Scorer / `includes()` | Requires the verifier success sentinel |
| isolated fixture | Sandbox | Docker image with the synthetic context case and verifier |
| transcripts and metrics | Inspect logs / `inspect view` | Inspect run log reviewed after each run |

Run the POC from `evals/inspect-poc` with a configured model provider:

```bash
python3 -m pip install inspect-ai
inspect eval context_skill_task.py --model <provider/model>
inspect view
```

The Docker sandbox must be available locally. The POC validates the evaluation shape; it does not claim that an arbitrary agent host can be bridged without host-specific authentication, tool permission, and transcript adapters.

## Recommendation

Adopt Inspect as an optional adapter for agentic or multi-trial suites after a team confirms Docker availability, model-provider credentials, log retention policy, and a host bridge. Keep the canonical task contract and deterministic Python checks framework-neutral.

This preserves Ascent's host-neutral skill architecture while allowing Inspect to provide repeatable agent loops, tool control, sandboxes, run logs, and inspection when those capabilities are needed.

## Constraints to resolve before direct adoption

- A current `inspect-ai` distribution must be available from the approved package source; the local package mirror used for this POC exposed only obsolete releases. The current official source requires Python 3.10 or later.
- Docker or an approved alternate sandbox must be available in the execution environment.
- Each target host needs an explicit bridge or equivalent agent harness; Inspect does not make a host's authenticated tools portable by itself.
- Logs can include prompts, tool calls, and artifacts. Set retention, redaction, and access policy before using client data.
- Model cost, rate limits, and non-determinism require a trial budget and reproducibility policy.

"""Inspect POC: agentic, sandboxed outcome evaluation for a synthetic context-skill case."""

from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import includes
from inspect_ai.tool import bash, todo_write


@task
def context_skill_agent_eval() -> Task:
    """Map a generated Ascent task contract to Inspect's agent evaluation primitives."""
    return Task(
        dataset=json_dataset("cases.json"),
        solver=react(
            prompt="You are validating an isolated synthetic Ascent context-skill fixture. Run the supplied verifier before answering. Do not read or use paths outside /opt/context-eval.",
            tools=[bash(), todo_write()],
            attempts=3,
        ),
        scorer=includes(),
        sandbox="docker",
    )

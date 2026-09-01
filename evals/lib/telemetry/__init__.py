"""Session-log parsers producing the `cost`, `time` and `behavior` blocks.

Public interface, identical across hosts:

    from evals.lib.telemetry import parse_session, HOSTS

    result = parse_session(path)          # host auto-detected from the path
    result = claude_code.parse_session(p)  # or call an adapter directly

`parse_session` returns a `SessionTelemetry` whose `.to_run_record(...)` builds an
`ascent.eval-run-record.v1` document. Every adapter guarantees:

* `cost`   - input / output / cache-read / cache-creation / total tokens,
             estimated USD (None when the model has no recorded rate),
             turns and tool_calls.
* `time`   - `agent_wall_clock_seconds` only. `human_baseline_minutes` is never
             invented here; a caller passes it in from a human record or omits it.
* `behavior` - skills invoked (deterministic pattern match) and clarifying
             questions asked. Limits are documented in each adapter's docstring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import claude_code, codex
from .model import CostBlock, SessionTelemetry, TimeBlock, BehaviorBlock

HOSTS = {
    "claude-code": claude_code,
    "codex": codex,
}

__all__ = [
    "HOSTS",
    "SessionTelemetry",
    "CostBlock",
    "TimeBlock",
    "BehaviorBlock",
    "claude_code",
    "codex",
    "detect_host",
    "parse_session",
]


def detect_host(path) -> str:
    """Return the host name for a session path.

    Detection is structural, not path-based where possible: a Claude Code
    session is newline-delimited JSON whose lines carry `type: "assistant"`;
    a Codex rollout carries `type: "session_meta"` / `"event_msg"`. Path hints
    (`.claude/projects`, `.codex/sessions`, a `rollout-` filename) are used as a
    tie-breaker only, so a session file copied elsewhere still parses.
    """
    p = Path(path)
    text_hint = None
    parts = {q.name for q in [p] + list(p.parents)}
    if ".codex" in parts or p.name.startswith("rollout-"):
        text_hint = "codex"
    elif ".claude" in parts:
        text_hint = "claude-code"

    try:
        with p.open("r", encoding="utf-8", errors="replace") as handle:
            for _ in range(40):
                line = handle.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    import json

                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                kind = record.get("type")
                if kind in ("session_meta", "event_msg", "response_item", "turn_context"):
                    return "codex"
                if kind in ("assistant", "user", "system", "file-history-snapshot"):
                    return "claude-code"
    except OSError:
        pass

    if text_hint:
        return text_hint
    raise ValueError(
        "cannot determine session host for {0}; pass --host explicitly".format(p)
    )


def parse_session(path, host: Optional[str] = None, **kwargs) -> SessionTelemetry:
    """Parse `path` with the adapter for `host` (auto-detected when omitted)."""
    name = host or detect_host(path)
    if name not in HOSTS:
        raise ValueError(
            "unknown host {0!r}; known hosts: {1}".format(name, ", ".join(sorted(HOSTS)))
        )
    return HOSTS[name].parse_session(path, **kwargs)

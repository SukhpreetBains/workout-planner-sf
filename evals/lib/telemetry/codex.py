"""Deterministic parser for Codex rollout logs.

IMPLEMENTED, NOT STUBBED. The shape below was confirmed by reading real files on
this machine on 2026-08-21, not guessed:

    ~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-<ISO-timestamp>-<uuid>.jsonl

24 files present, 9 of them with cwd `/Users/andrewfischer/Projects/ascent`.
Newline-delimited JSON; every line carries a top-level `timestamp` and `type`.
Confirmed line types and the fields this parser reads:

    {"type": "session_meta",  "payload": {"session_id", "cwd", "cli_version",
                                          "originator", "model_provider", ...}}
    {"type": "turn_context",  "payload": {"model", "effort", "cwd", ...}}
    {"type": "event_msg",     "payload": {"type": "token_count",
        "info": {"total_token_usage": {...}, "last_token_usage": {...},
                 "model_context_window": 258400}}}
    {"type": "response_item", "payload": {"type": "custom_tool_call" |
        "function_call" | "local_shell_call" | "message" | "reasoning", ...}}

Codex's token accounting is NOT shaped like Claude Code's, and the difference
matters for pricing:

    total_token_usage = {
        input_tokens,              # INCLUDES cached_input_tokens
        cached_input_tokens,       # subset of input_tokens
        cache_write_input_tokens,  # 0 in every observed session (see caveat)
        output_tokens,             # INCLUDES reasoning_output_tokens
        reasoning_output_tokens,   # subset of output_tokens
        total_tokens,              # == input_tokens + output_tokens
    }

Confirmed arithmetically on a real session: input 16184 + output 144 = total
16328, with cached_input_tokens 4864 inside the 16184. So this parser maps

    cost.cache_read_tokens     = cached_input_tokens
    cost.input_tokens          = input_tokens - cached_input_tokens   (uncached)
    cost.cache_creation_tokens = cache_write_input_tokens
    cost.output_tokens         = output_tokens                        (as reported)

which keeps `total_tokens` in the run record equal to Codex's own `total_tokens`
and keeps cache reads priced separately, exactly as the spec requires.

`total_token_usage` is cumulative, so this parser takes the maximum observed
rather than the last observed: files that resume or fork a thread contain several
`session_meta` lines (one ascent file has 12), and a cumulative counter cannot be
assumed monotonic across those boundaries.

CAVEATS RECORDED HONESTLY - what is NOT confirmed
-------------------------------------------------
1. `cache_write_input_tokens` is 0 in all 24 files on this machine, including a
   641-line session with 8.5M input tokens. Whether it is a *subset* of
   `input_tokens` (like `cached_input_tokens`) or an *additional* charge (like
   Claude Code's `cache_creation_input_tokens`) is therefore unverified. This
   parser treats it as a subset and subtracts it from uncached input only when
   non-zero, flagging `cache_write_semantics_unverified` in `parse_stats` so the
   assumption is visible rather than silent. Confirm against a session that
   actually writes cache before quoting a cache-write cost.
2. There is no per-token rate on file for the Codex models observed
   (`gpt-5.6-terra`, `codex-auto-review`). `estimated_usd` is therefore None, not
   0.0, and `parse_stats.unpriced_model` names the model. Add a rate to
   pricing.json with a `checked_on` date before quoting dollars for Codex.
3. Skill invocation detection is weaker here than on Claude Code. Codex has no
   `Skill` tool; the only signal is a shell command touching a `skills/` path,
   read out of `custom_tool_call` / `local_shell_call` arguments. A Codex run
   that follows skill instructions without shelling into `skills/` records no
   skill invocation.
4. Codex has no `AskUserQuestion` equivalent, so the clarifying-question count
   rests entirely on the question-mark heuristic over `agent_message` text. Treat
   it as a loose upper bound; the exact-count channel that exists on Claude Code
   does not exist here.
5. A rollout file can hold a *resumed* thread - one ascent file carries 12
   `session_meta` lines and spans 6.8 days of wall clock. First-to-last timestamp
   is then elapsed calendar time, not time on task. `parse_stats` sets
   `wall_clock_spans_multiple_sessions` and adds `wall_clock_caveat` whenever this
   is the case, so an eval never quietly quotes a week as an agent runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import pricing as _pricing
from .behavior import QuestionDetector, SkillDetector
from .model import (
    BehaviorBlock,
    CostBlock,
    SessionTelemetry,
    TimeBlock,
    parse_iso8601,
    to_iso8601_z,
)

HOST_NAME = "codex"
TELEMETRY_SOURCE = "codex-rollout-jsonl"

TOOL_CALL_PAYLOAD_TYPES = (
    "custom_tool_call",
    "function_call",
    "local_shell_call",
    "mcp_tool_call",
)


def _iter_lines(path: Path) -> Iterable[Tuple[int, Optional[Dict[str, Any]]]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for number, raw in enumerate(handle, start=1):
            text = raw.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except ValueError:
                yield number, None
                continue
            if not isinstance(obj, dict):
                yield number, None
                continue
            yield number, obj


def _int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def _command_strings(payload: Dict[str, Any]) -> List[str]:
    """Pull anything command-shaped out of a tool-call payload."""
    out: List[str] = []
    for key in ("input", "arguments", "command", "cmd"):
        value = payload.get(key)
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            out.append(" ".join(str(part) for part in value))
        elif isinstance(value, dict):
            for nested in value.values():
                if isinstance(nested, str):
                    out.append(nested)
                elif isinstance(nested, list):
                    out.append(" ".join(str(part) for part in nested))
    return out


def _message_text(payload: Dict[str, Any]) -> List[str]:
    """Extract assistant-visible text from a message / agent_message payload."""
    out: List[str] = []
    message = payload.get("message")
    if isinstance(message, str):
        out.append(message)
    content = payload.get("content")
    if isinstance(content, str):
        out.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    out.append(text)
            elif isinstance(block, str):
                out.append(block)
    text = payload.get("text")
    if isinstance(text, str):
        out.append(text)
    return out


def parse_session(
    path,
    cache_write_ttl: Optional[str] = None,
    pricing_data: Optional[Dict[str, Any]] = None,
    include_subagents: bool = True,
) -> SessionTelemetry:
    """Parse a Codex rollout file into a `SessionTelemetry`.

    `include_subagents` is accepted for interface parity with the Claude Code
    adapter and has no effect: Codex writes subagent activity (the `guardian` /
    auto-review threads) into its own rollout files rather than sidecars, so
    there is nothing extra to fold in from a single file.
    """
    main = Path(path)
    if not main.is_file():
        raise FileNotFoundError("no such session file: {0}".format(main))

    skills = SkillDetector()
    questions = QuestionDetector()

    timestamps: List[Any] = []
    malformed = 0
    tool_calls = 0
    turns = 0
    models: List[str] = []
    cli_version: Optional[str] = None
    session_meta_lines = 0
    token_count_events = 0
    best: Optional[Dict[str, int]] = None
    best_total = -1

    for _number, record in _iter_lines(main):
        if record is None:
            malformed += 1
            continue

        moment = parse_iso8601(record.get("timestamp"))
        if moment is not None:
            timestamps.append(moment)

        kind = record.get("type")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        if kind == "session_meta":
            session_meta_lines += 1
            version = payload.get("cli_version")
            if isinstance(version, str) and not cli_version:
                cli_version = version
            continue

        if kind == "turn_context":
            model = payload.get("model")
            if isinstance(model, str) and model and model not in models:
                models.append(model)
            continue

        if kind == "event_msg":
            event = payload.get("type")
            if event == "token_count":
                token_count_events += 1
                info = payload.get("info")
                if isinstance(info, dict):
                    usage = info.get("total_token_usage")
                    if isinstance(usage, dict):
                        total = _int(usage.get("total_tokens"))
                        if total > best_total:
                            best_total = total
                            best = {
                                "input_tokens": _int(usage.get("input_tokens")),
                                "cached_input_tokens": _int(usage.get("cached_input_tokens")),
                                "cache_write_input_tokens": _int(
                                    usage.get("cache_write_input_tokens")
                                ),
                                "output_tokens": _int(usage.get("output_tokens")),
                                "reasoning_output_tokens": _int(
                                    usage.get("reasoning_output_tokens")
                                ),
                                "total_tokens": total,
                            }
            elif event == "agent_message":
                turns += 1
                for text in _message_text(payload):
                    questions.observe_text(text)
            continue

        if kind == "response_item":
            item = payload.get("type")
            if item in TOOL_CALL_PAYLOAD_TYPES:
                tool_calls += 1
                for command in _command_strings(payload):
                    skills.observe_tool_use({"name": "Bash", "input": {"command": command}})
            continue

    usage = best or {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
        "total_tokens": 0,
    }

    cache_read = usage["cached_input_tokens"]
    cache_write = usage["cache_write_input_tokens"]
    # cached_input_tokens is confirmed to be a subset of input_tokens.
    # cache_write_input_tokens is assumed to be a subset too - unverified,
    # because it is 0 in every session on this machine. Clamp at zero so an
    # inverted assumption can never produce a negative token count.
    uncached_input = max(usage["input_tokens"] - cache_read - cache_write, 0)

    started = min(timestamps) if timestamps else None
    ended = max(timestamps) if timestamps else None
    wall_clock = None
    if started is not None and ended is not None:
        wall_clock = round((ended - started).total_seconds(), 3)

    model = models[0] if models else None
    estimated = _pricing.price_usage(
        model,
        input_tokens=uncached_input,
        output_tokens=usage["output_tokens"],
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_write,
        cache_write_ttl=cache_write_ttl,
        pricing=pricing_data,
    )

    cost = CostBlock(
        input_tokens=uncached_input,
        output_tokens=usage["output_tokens"],
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_write,
        estimated_usd=estimated,
        turns=turns,
        tool_calls=tool_calls,
    )

    parse_stats: Dict[str, Any] = {
        "host": HOST_NAME,
        "malformed_lines": malformed,
        "session_meta_lines": session_meta_lines,
        "token_count_events": token_count_events,
        "token_usage_selection": "max(total_token_usage.total_tokens) across token_count events",
        "wall_clock_spans_multiple_sessions": session_meta_lines > 1,
        "reported_total_tokens": usage["total_tokens"],
        "reasoning_output_tokens_included_in_output": usage["reasoning_output_tokens"],
        "cache_write_semantics_unverified": cache_write == 0,
        "cache_write_ttl_assumed": cache_write_ttl or _default_cache_ttl(pricing_data),
        "pricing_checked_on": _pricing.checked_on(model, pricing_data),
        "unpriced_model": model if estimated is None and model else None,
        "questions": questions.breakdown(),
        "skills": skills.breakdown(),
        "known_limits": [
            "no Skill tool in Codex; skill detection is shell-path only",
            "no AskUserQuestion equivalent; question count is heuristic only",
            "cache_write_input_tokens observed as 0 in every local session",
        ],
    }

    if session_meta_lines > 1:
        parse_stats["wall_clock_caveat"] = (
            "this rollout contains {0} session_meta lines, so it records a resumed or "
            "forked thread. First-to-last timestamp therefore spans the idle gaps "
            "between sittings and is not one run's wall clock. Use a rollout with a "
            "single session_meta for a time measurement.".format(session_meta_lines)
        )

    if cost.total_tokens != usage["total_tokens"] and usage["total_tokens"]:
        parse_stats["total_tokens_reconciliation"] = {
            "codex_reported": usage["total_tokens"],
            "run_record_total": cost.total_tokens,
            "note": (
                "difference means cache_write_input_tokens was non-zero and the "
                "subset assumption may be wrong; verify against Codex billing"
            ),
        }

    return SessionTelemetry(
        host_name=HOST_NAME,
        session_path=str(main),
        telemetry_source=TELEMETRY_SOURCE,
        cost=cost,
        time=TimeBlock(agent_wall_clock_seconds=wall_clock),
        behavior=BehaviorBlock(
            skills_invoked=skills.invoked(),
            clarifying_questions_asked=questions.total(),
        ),
        host_version=cli_version,
        models=list(models),
        started_at=to_iso8601_z(started),
        ended_at=to_iso8601_z(ended),
        parse_stats=parse_stats,
    )


def _default_cache_ttl(pricing_data: Optional[Dict[str, Any]]) -> str:
    data = pricing_data if pricing_data is not None else _pricing.load_pricing()
    return data.get("cache_write_default_ttl", "5m")

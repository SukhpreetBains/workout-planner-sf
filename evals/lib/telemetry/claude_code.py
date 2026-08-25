"""Deterministic parser for Claude Code session logs.

File layout, confirmed against real sessions under
`~/.claude/projects/-Users-andrewfischer-Projects-ascent/` on 2026-08-21:

    ~/.claude/projects/<path-slug>/<session-uuid>.jsonl        main transcript
    ~/.claude/projects/<path-slug>/<session-uuid>/subagents/
        agent-<id>.jsonl                                       subagent transcript
        agent-<id>.meta.json                                   {agentType, description, ...}

Newline-delimited JSON, one object per line. Every line carries `timestamp`
(ISO-8601 with a trailing Z). `type: "assistant"` lines carry `message.usage`
with `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
`cache_creation_input_tokens`, and `message.model`. Tool calls appear as
`tool_use` content blocks inside assistant messages.

Two double-counting traps, both handled here:

1. **One assistant message is split across several JSONL lines, one per content
   block, and every line repeats the same `message.usage`.** This is the big one
   and it contradicts the spec's "sum usage across assistant lines" instruction.
   In the three ascent sessions, naive summation inflates totals by 1.76x-2.01x
   (e.g. 8ef5b54d: 2,661,563 cache-read tokens naive vs 1,349,247 real). Usage is
   therefore counted once per unique `message.id`, falling back to `requestId`
   and then the line `uuid` when an id is absent. Content blocks are collected
   from *every* line (they are partitioned across lines, not repeated), and
   deduplicated by `tool_use` block id so either layout is safe.

2. **`message.usage.iterations[]` repeats the top-level figures per inference
   iteration.** Never summed here. Across all 399 session files on this machine
   the array is always length 1 or absent, so it has never actually inflated a
   figure - but summing it would double-count the moment a session uses
   server-side fallback or multi-iteration inference.

Subagent transcripts are included by default, because excluding them badly
understates cost: in session 8ef5b54d the four subagents account for ~1.20M
cache-read tokens against the main thread's 1.35M. `include_subagents=False`
gives the main-thread-only figures, and `parse_stats` always reports the split.

PER-CALL DURATIONS
------------------
Calvin asked for the timing one level below the conversation: "Did that skill
call out? How long did that skill call out take? Or how long did the full
conversation take as compared to one that didn't have that skill." The full
conversation is first-to-last timestamp. The per-call figure is recoverable from
data this parser already reads and previously threw away - it collected every
timestamp and then used only `min()` and `max()`.

A tool call is an assistant `tool_use` block; its result is a `user` line whose
`message.content[]` holds a `tool_result` with the matching `tool_use_id`, and
that line carries its own `timestamp`. The duration of a call is the difference.
Calls whose result never appears - the session was still running, or the call was
interrupted - are counted as unmatched rather than given a duration.

Skill attribution per call uses `behavior.skills_in_tool_use`, so a timed call is
attributed by exactly the rules that produce `skills_invoked`, and inherits the
same blind spots: a skill followed without invoking the `Skill` tool or touching
a `skills/` path is untimed because it is undetected.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from . import pricing as _pricing
from .behavior import QuestionDetector, SkillDetector, skills_in_tool_use
from .model import (
    BehaviorBlock,
    CostBlock,
    SessionTelemetry,
    TimeBlock,
    parse_iso8601,
    to_iso8601_z,
)

HOST_NAME = "claude-code"
TELEMETRY_SOURCE = "claude-code-session-jsonl"

USAGE_FIELDS = (
    ("input_tokens", "input_tokens"),
    ("output_tokens", "output_tokens"),
    ("cache_read_input_tokens", "cache_read_tokens"),
    ("cache_creation_input_tokens", "cache_creation_tokens"),
)

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _iter_lines(path: Path) -> Iterable[Tuple[int, Optional[Dict[str, Any]]]]:
    """Yield (line_number, parsed_object_or_None) tolerating malformed lines.

    Real session files can end in a partially written line if the host was still
    running or was killed mid-write; a truncated or non-object line yields None
    and is counted rather than raising.
    """
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


def subagent_paths(session_path) -> List[Path]:
    """Return subagent transcripts for a main session file, sorted by name."""
    main = Path(session_path)
    sidecar = main.parent / main.stem / "subagents"
    if not sidecar.is_dir():
        return []
    return sorted(p for p in sidecar.glob("agent-*.jsonl") if p.is_file())


def _usage_identity(record: Dict[str, Any], message: Dict[str, Any]) -> str:
    """Stable per-inference-response key used to count usage exactly once."""
    for candidate in (message.get("id"), record.get("requestId"), record.get("uuid")):
        if candidate:
            return str(candidate)
    return "line:{0}".format(id(record))


class _Accumulator:
    def __init__(self) -> None:
        self.tokens = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
        }
        self.seen_usage: Set[str] = set()
        self.seen_tool_use: Set[str] = set()
        self.assistant_lines = 0
        self.assistant_messages = 0
        self.malformed_lines = 0
        self.tool_calls = 0
        self.models: List[str] = []
        self.timestamps: List[Any] = []
        self.iterations_seen = 0
        self.iterations_skipped_tokens = 0
        # Per-request usage deltas, one entry per deduplicated assistant message.
        self.per_request: List[Dict[str, Any]] = []
        # tool_use id -> the call we are waiting on a tool_result for.
        self.open_calls: Dict[str, Dict[str, Any]] = {}
        self.completed_calls: List[Dict[str, Any]] = []
        self.unmatched_results = 0

    def note_model(self, model: Optional[str]) -> None:
        if model and model not in self.models:
            self.models.append(model)


def _consume(
    path: Path,
    acc: _Accumulator,
    skills: SkillDetector,
    questions: QuestionDetector,
    is_sidechain_file: bool,
) -> Dict[str, int]:
    local = {"assistant_lines": 0, "assistant_messages": 0, "malformed_lines": 0}
    for _number, record in _iter_lines(path):
        if record is None:
            acc.malformed_lines += 1
            local["malformed_lines"] += 1
            continue

        moment = parse_iso8601(record.get("timestamp"))
        if moment is not None:
            acc.timestamps.append(moment)

        if record.get("type") == "user":
            # A tool_result closes the call that opened it. This is the only
            # channel that dates the *end* of a tool call.
            _close_tool_calls(record, acc, moment)
            continue

        if record.get("type") != "assistant":
            continue

        message = record.get("message")
        if not isinstance(message, dict):
            continue

        acc.assistant_lines += 1
        local["assistant_lines"] += 1
        acc.note_model(message.get("model"))

        usage = message.get("usage")
        identity = _usage_identity(record, message)
        if isinstance(usage, dict) and identity not in acc.seen_usage:
            acc.seen_usage.add(identity)
            acc.assistant_messages += 1
            local["assistant_messages"] += 1
            request: Dict[str, Any] = {
                "request_index": acc.assistant_messages,
                "message_id": identity,
                "model": message.get("model"),
                "timestamp": to_iso8601_z(moment),
                "from_subagent": is_sidechain_file,
            }
            for wire, field in USAGE_FIELDS:
                value = usage.get(wire)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    request[field] = 0
                    continue
                acc.tokens[field] += int(value)
                request[field] = int(value)
            request["total_tokens"] = sum(
                request[field] for _wire, field in USAGE_FIELDS
            )
            # Claude Code does not report a reasoning-token subtotal. None means
            # "the host does not report it", not "zero".
            request["reasoning_output_tokens"] = None
            acc.per_request.append(request)
            # Trap 2: iterations[] restates the same figures. Measure, never add.
            iterations = usage.get("iterations")
            if isinstance(iterations, list):
                acc.iterations_seen += len(iterations)
                for entry in iterations:
                    if not isinstance(entry, dict):
                        continue
                    for wire, _field in USAGE_FIELDS:
                        value = entry.get(wire)
                        if isinstance(value, (int, float)) and not isinstance(value, bool):
                            acc.iterations_skipped_tokens += int(value)

        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "tool_use":
                block_id = block.get("id") or "{0}:{1}".format(identity, block.get("name"))
                if block_id in acc.seen_tool_use:
                    continue
                acc.seen_tool_use.add(block_id)
                acc.tool_calls += 1
                skills.observe_tool_use(block)
                questions.observe_tool_use(block, from_subagent=is_sidechain_file)
                if moment is not None:
                    acc.open_calls[str(block_id)] = {
                        "tool": block.get("name"),
                        "skills": skills_in_tool_use(block),
                        "started": moment,
                        "from_subagent": is_sidechain_file,
                        "file": path.name,
                    }
            elif kind == "text":
                questions.observe_text(block.get("text"), from_subagent=is_sidechain_file)
    return local


# What a call's duration is actually the duration *of*. This matters more than it
# looks. Invoking the `Skill` tool injects the skill body into context and
# returns almost immediately - measured at 0.07-0.09 s on real sessions - so that
# number is a tool round trip and emphatically NOT "how long the skill took". The
# work a skill directs happens afterwards, spread across later turns and tool
# calls, and nothing in the transcript brackets it. A Bash call into a skill's
# scripts is different: that duration is the script actually running.
_WHAT_A_DURATION_MEASURES = {
    "Skill": (
        "tool round trip only. The Skill tool injects instructions into context and "
        "returns; the work it directs happens in later turns and is not bracketed "
        "anywhere in the transcript. Do not read this as the cost of the skill."
    ),
    "Bash": "the subprocess ran for this long.",
    None: "time from the tool call to its result line.",
}


def _close_tool_calls(record: Dict[str, Any], acc: "_Accumulator", moment: Any) -> None:
    """Close any tool call this `user` line reports a result for.

    Claude Code returns tool results as `tool_result` content blocks on a `user`
    line, keyed by `tool_use_id`. That line's own timestamp is the only record of
    when the call finished.
    """
    message = record.get("message")
    if not isinstance(message, dict):
        return
    content = message.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        call_id = block.get("tool_use_id")
        if not call_id:
            continue
        opened = acc.open_calls.pop(str(call_id), None)
        if opened is None:
            acc.unmatched_results += 1
            continue
        if moment is None:
            acc.open_calls[str(call_id)] = opened
            continue
        acc.completed_calls.append(
            {
                "tool_use_id": str(call_id),
                "tool": opened["tool"],
                "skills": list(opened["skills"]),
                "from_subagent": opened["from_subagent"],
                "transcript": opened["file"],
                "started_at": to_iso8601_z(opened["started"]),
                "ended_at": to_iso8601_z(moment),
                "duration_seconds": round((moment - opened["started"]).total_seconds(), 3),
                "duration_measures": _WHAT_A_DURATION_MEASURES.get(
                    opened["tool"], _WHAT_A_DURATION_MEASURES[None]
                ),
            }
        )


def _call_timing(acc: "_Accumulator") -> Dict[str, Any]:
    """Per-skill-call and all-tool-call durations, plus what could not be matched."""
    skill_calls = [call for call in acc.completed_calls if call["skills"]]
    by_skill: Dict[str, Any] = {}
    for call in skill_calls:
        for skill in call["skills"]:
            bucket = by_skill.setdefault(skill, {"calls": 0, "total_seconds": 0.0, "durations": []})
            bucket["calls"] += 1
            bucket["total_seconds"] = round(bucket["total_seconds"] + call["duration_seconds"], 3)
            bucket["durations"].append(call["duration_seconds"])
    for skill, bucket in by_skill.items():
        durations = bucket.pop("durations")
        bucket["max_seconds"] = round(max(durations), 3)
        bucket["p50_seconds"] = round(_median(durations), 3)

    all_durations = [call["duration_seconds"] for call in acc.completed_calls]
    tool_call_seconds: Optional[Dict[str, Any]] = None
    if all_durations:
        tool_call_seconds = {
            "calls_timed": len(all_durations),
            "calls_unmatched": len(acc.open_calls),
            "orphan_results": acc.unmatched_results,
            "total_seconds": round(sum(all_durations), 3),
            "p50_seconds": round(_median(all_durations), 3),
            "max_seconds": round(max(all_durations), 3),
        }
        if acc.open_calls:
            tool_call_seconds["calls_unmatched_reason"] = (
                "No tool_result line carried these tool_use ids. The session was "
                "still running, or the call was interrupted, so they have no "
                "duration rather than a zero one."
            )
    if by_skill:
        for skill, bucket in by_skill.items():
            bucket["tools"] = sorted(
                set(
                    str(call["tool"])
                    for call in skill_calls
                    if skill in call["skills"] and call["tool"]
                )
            )
            if bucket["tools"] == ["Skill"]:
                bucket["reading"] = _WHAT_A_DURATION_MEASURES["Skill"]
    return {
        "skill_calls": skill_calls,
        "skill_call_seconds_by_skill": by_skill,
        "tool_call_seconds": tool_call_seconds,
    }


def _median(values: List[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def parse_session(
    path,
    include_subagents: bool = True,
    cache_write_ttl: Optional[str] = None,
    pricing_data: Optional[Dict[str, Any]] = None,
) -> SessionTelemetry:
    """Parse a Claude Code session (and its subagents) into a `SessionTelemetry`.

    Args:
        path: the `<session-uuid>.jsonl` transcript.
        include_subagents: count `<session-uuid>/subagents/agent-*.jsonl` too.
            Default True; leaving them out understates cost by roughly half on
            sessions that fan out.
        cache_write_ttl: `"5m"` (default) or `"1h"`. Session logs record
            `usage.cache_creation.ephemeral_5m_input_tokens` /
            `ephemeral_1h_input_tokens`, but the aggregate
            `cache_creation_input_tokens` field does not distinguish them, so the
            TTL is a caller-supplied assumption rather than something parsed.
        pricing_data: override for tests.
    """
    main = Path(path)
    if not main.is_file():
        raise FileNotFoundError("no such session file: {0}".format(main))

    acc = _Accumulator()
    skills = SkillDetector()
    questions = QuestionDetector()

    main_stats = _consume(main, acc, skills, questions, is_sidechain_file=False)

    subagents: List[Dict[str, Any]] = []
    if include_subagents:
        for sub in subagent_paths(main):
            before = dict(acc.tokens)
            sub_stats = _consume(sub, acc, skills, questions, is_sidechain_file=True)
            meta_path = sub.parent / (sub.stem + ".meta.json")
            meta: Dict[str, Any] = {}
            if meta_path.is_file():
                try:
                    with meta_path.open("r", encoding="utf-8") as handle:
                        loaded = json.load(handle)
                    if isinstance(loaded, dict):
                        meta = loaded
                except (OSError, ValueError):
                    meta = {}
            subagents.append(
                {
                    "file": sub.name,
                    "agent_type": meta.get("agentType"),
                    "description": meta.get("description"),
                    "assistant_messages": sub_stats["assistant_messages"],
                    "tokens": {
                        key: acc.tokens[key] - before[key] for key in acc.tokens
                    },
                }
            )

    started = min(acc.timestamps) if acc.timestamps else None
    ended = max(acc.timestamps) if acc.timestamps else None
    wall_clock = None
    if started is not None and ended is not None:
        wall_clock = round((ended - started).total_seconds(), 3)

    model = acc.models[0] if acc.models else None
    estimated = _pricing.price_usage(
        model,
        input_tokens=acc.tokens["input_tokens"],
        output_tokens=acc.tokens["output_tokens"],
        cache_read_tokens=acc.tokens["cache_read_tokens"],
        cache_creation_tokens=acc.tokens["cache_creation_tokens"],
        cache_write_ttl=cache_write_ttl,
        pricing=pricing_data,
    )

    # Context window comes from the rate card entry for the model, so a
    # utilisation figure is derived from a recorded number rather than a guess.
    context_window = _context_window(model, pricing_data)
    utilisation: List[float] = []
    if context_window:
        for entry in acc.per_request:
            live_context = (
                entry["input_tokens"]
                + entry["cache_read_tokens"]
                + entry["cache_creation_tokens"]
            )
            ratio = live_context / float(context_window)
            entry["context_utilization"] = round(ratio, 6)
            utilisation.append(ratio)

    cost = CostBlock(
        input_tokens=acc.tokens["input_tokens"],
        output_tokens=acc.tokens["output_tokens"],
        cache_read_tokens=acc.tokens["cache_read_tokens"],
        cache_creation_tokens=acc.tokens["cache_creation_tokens"],
        estimated_usd=estimated,
        turns=acc.assistant_messages,
        tool_calls=acc.tool_calls,
        # Claude Code reports no reasoning-token subtotal. None, never 0.
        reasoning_output_tokens=None,
        per_request=acc.per_request,
        context_window=context_window,
        peak_context_utilization=round(max(utilisation), 6) if utilisation else None,
        credits=None,
        credits_unavailable_reason=(
            "Credits are the Codex / ChatGPT billing unit. Claude Code sessions are "
            "billed in dollars, which is what estimated_usd reports."
        ),
        model_requests=acc.assistant_messages,
    )

    timing = _call_timing(acc)

    behavior = BehaviorBlock(
        skills_invoked=skills.invoked(),
        clarifying_questions_asked=questions.total(),
    )

    parse_stats: Dict[str, Any] = {
        "host": HOST_NAME,
        "assistant_lines": acc.assistant_lines,
        "assistant_messages_deduplicated": acc.assistant_messages,
        "line_to_message_inflation_avoided": (
            round(acc.assistant_lines / acc.assistant_messages, 3)
            if acc.assistant_messages
            else None
        ),
        "usage_iterations_entries_ignored": acc.iterations_seen,
        "usage_iterations_tokens_not_double_counted": acc.iterations_skipped_tokens,
        "malformed_lines": acc.malformed_lines,
        "main_transcript": {
            "file": main.name,
            "assistant_messages": main_stats["assistant_messages"],
            "malformed_lines": main_stats["malformed_lines"],
        },
        "subagents_included": include_subagents,
        "subagent_count": len(subagents),
        "subagents": subagents,
        "tool_calls_timed": len(acc.completed_calls),
        "tool_calls_without_a_result_line": len(acc.open_calls),
        "tool_results_without_a_matching_call": acc.unmatched_results,
        "context_window_source": (
            "pricing.json context_tokens for {0}".format(model) if model else None
        ),
        "cache_write_ttl_assumed": cache_write_ttl or _default_cache_ttl(pricing_data),
        "pricing_checked_on": _pricing.checked_on(model, pricing_data),
        "unpriced_model": model if estimated is None and model else None,
        "questions": questions.breakdown(),
        "skills": skills.breakdown(),
    }

    return SessionTelemetry(
        host_name=HOST_NAME,
        session_path=str(main),
        telemetry_source=TELEMETRY_SOURCE,
        cost=cost,
        time=TimeBlock(
            agent_wall_clock_seconds=wall_clock,
            skill_calls=timing["skill_calls"],
            skill_call_seconds_by_skill=timing["skill_call_seconds_by_skill"],
            tool_call_seconds=timing["tool_call_seconds"],
            skill_call_timing_unavailable_reason=(
                "No tool call in this session was attributable to a skill, so there "
                "is nothing to time. Skill detection sees the Skill tool and Bash "
                "paths into skills/<name>/ only."
            ),
        ),
        behavior=behavior,
        host_version=_host_version(main),
        models=list(acc.models),
        started_at=to_iso8601_z(started),
        ended_at=to_iso8601_z(ended),
        parse_stats=parse_stats,
    )


def _context_window(model: Optional[str], pricing_data: Optional[Dict[str, Any]]) -> Optional[int]:
    """The model's context window from pricing.json, or None when unrecorded."""
    if not model:
        return None
    data = pricing_data if pricing_data is not None else _pricing.load_pricing()
    key = _pricing.normalise_model(model, data)
    if key is None:
        return None
    value = data["models"][key].get("context_tokens")
    return int(value) if isinstance(value, int) else None


def _default_cache_ttl(pricing_data: Optional[Dict[str, Any]]) -> str:
    data = pricing_data if pricing_data is not None else _pricing.load_pricing()
    return data.get("cache_write_default_ttl", "5m")


def _host_version(path: Path) -> Optional[str]:
    """Read the Claude Code `version` field off the first line that carries one."""
    for _number, record in _iter_lines(path):
        if record is None:
            continue
        version = record.get("version")
        if isinstance(version, str) and version:
            return version
    return None

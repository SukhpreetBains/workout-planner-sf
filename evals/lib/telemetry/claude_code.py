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
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

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
            for wire, field in USAGE_FIELDS:
                value = usage.get(wire)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                acc.tokens[field] += int(value)
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
            elif kind == "text":
                questions.observe_text(block.get("text"), from_subagent=is_sidechain_file)
    return local


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

    cost = CostBlock(
        input_tokens=acc.tokens["input_tokens"],
        output_tokens=acc.tokens["output_tokens"],
        cache_read_tokens=acc.tokens["cache_read_tokens"],
        cache_creation_tokens=acc.tokens["cache_creation_tokens"],
        estimated_usd=estimated,
        turns=acc.assistant_messages,
        tool_calls=acc.tool_calls,
    )

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
        time=TimeBlock(agent_wall_clock_seconds=wall_clock),
        behavior=behavior,
        host_version=_host_version(main),
        models=list(acc.models),
        started_at=to_iso8601_z(started),
        ended_at=to_iso8601_z(ended),
        parse_stats=parse_stats,
    )


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

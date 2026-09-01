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

CREDITS: THE BILLING UNIT IS A TURN, NOT A REQUEST
--------------------------------------------------
Credits come from `credits.py` and the frozen `codex_rates.json`. Two things
about the derivation are load-bearing and both were measured, not assumed.

**Group by turn.** The published "5-30 credits per message" band is per *user
turn*. `turn_context` carries the `turn_id`, the effective `model` and the
`effort`, so it is the join key for applying a rate; `token_count` events carry
no turn id at all, so attribution is positional - every `token_count` belongs to
the most recent `turn_context`. Measured across the 26 local rollouts on
2026-08-25: 223 turns, 1148 model requests, and on the 58 turns whose model is
on the rate card a median of 5 and a mean of 11.8 requests per turn. Quoting a
per-request figure against the published per-message band therefore understates
by roughly an order of magnitude. Both spreads are emitted and both carry their
unit.

Only `turn_context` advances the attribution pointer. `task_started` also carries
a `turn_id`, and letting it open a new bucket splits 223 turns into 228 and moves
requests between them; the turn_context-only grouping is the one that reproduces
the rate card's own measurement exactly.

**`codex-auto-review` is a router alias, not a model.** It is what a `guardian`
subagent thread records as its model, and its own `collaboration_mode.settings`
repeats the alias, so it cannot be resolved from within a single `turn_context`.
Resolution order, with the method recorded per turn in `model_resolution` so a
reader can see which one applied:

  1. `turn_context` names a model that is on the rate card - use it.
  2. An earlier `turn_context` in the same file names a real model - use that.
  3. `session_meta.parent_thread_id` names the thread that spawned this one;
     the sibling rollout file whose name ends in that id is read for its
     prevailing model. Verified: the auto-review thread beside
     `rollout-2026-08-13T13-58-48` resolves to its parent's `gpt-5.6-sol`.
  4. Otherwise `None`. An unresolved alias emits null credits, never zero.

`gpt-5.5` is a different case: it is a real model that is genuinely off the
current rate card (superseded), so it stays null however it is reached.

**Reconciliation is reported, never repaired.** The card records the invariant
`total_token_usage[i].total - total_token_usage[i-1].total ==
last_token_usage[i].total`. Re-derived here on the 26 local rollouts: it holds
1108 times and fails 13, clustering at compaction and resume boundaries where
the context is rebuilt. The failures are counted and surfaced in
`cost.credits.reconciliation_invariant`; nothing silently reconciles them,
because a repaired delta would be an invented token count.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import credits as _credits
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

# Emitting one entry per model request is what makes an in-run spread visible.
# A pathological rollout has 174 requests in a single turn, so the array is
# bounded and the truncation is declared rather than silent.
MAX_PER_REQUEST_ENTRIES = 1000

USAGE_DELTA_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
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


def _usage_dict(source: Any) -> Dict[str, int]:
    """Normalise a Codex usage object into every field this parser prices from."""
    if not isinstance(source, dict):
        return dict((key, 0) for key in USAGE_DELTA_FIELDS)
    return dict((key, _int(source.get(key))) for key in USAGE_DELTA_FIELDS)


def _sessions_root(path: Path) -> Optional[Path]:
    """The `sessions` directory a rollout lives under, if the layout is the usual one."""
    for parent in path.parents:
        if parent.name == "sessions":
            return parent
    return None


def _parent_thread_model(main: Path, parent_thread_id: str, rates: Any) -> Optional[Dict[str, str]]:
    """Resolve a router alias by reading the parent thread's prevailing model.

    A `guardian` / auto-review rollout records `codex-auto-review` as its own
    model, which is not a billable model. `session_meta.parent_thread_id` names
    the thread that spawned it, and rollout filenames end in their thread id, so
    the parent file can be found deterministically and read for the last real
    model it ran. Returns None rather than guessing when the parent is absent.
    """
    root = _sessions_root(main)
    if root is None or not parent_thread_id:
        return None
    matches = sorted(root.rglob("rollout-*{0}*.jsonl".format(parent_thread_id)))
    for candidate in matches:
        if candidate == main:
            continue
        resolved: Optional[str] = None
        for _number, record in _iter_lines(candidate):
            if record is None or record.get("type") != "turn_context":
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            model = payload.get("model")
            if isinstance(model, str) and model and not _credits.is_router_alias(model, rates):
                resolved = model
        if resolved:
            return {"model": resolved, "source_file": candidate.name}
    return None


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
    rates_data: Optional[Dict[str, Any]] = None,
    infer_router_alias_model: bool = False,
) -> SessionTelemetry:
    """Parse a Codex rollout file into a `SessionTelemetry`.

    `include_subagents` is accepted for interface parity with the Claude Code
    adapter and has no effect: Codex writes subagent activity (the `guardian` /
    auto-review threads) into its own rollout files rather than sidecars, so
    there is nothing extra to fold in from a single file.

    `infer_router_alias_model` is **off by default, deliberately.** When a
    `turn_context` records `codex-auto-review`, the rate card's instruction is to
    resolve the effective model *from the turn_context event*; measured on the 26
    local rollouts it is not there - `collaboration_mode.settings.model` repeats
    the alias and auto-review threads name no other model - so the honest result
    for those turns is null credits.

    Turning this flag on enables two *inferences* rather than resolutions: the
    last real model named earlier in the same file, then the prevailing model of
    the parent thread named by `session_meta.parent_thread_id`. Both assume a
    review subagent bills at its parent\'s rate, which nothing on file
    establishes. On this corpus the flag prices 148 further turns and moves the
    session median from 2.59 to 0.70 credits per turn - a material change to a
    client-facing figure on the strength of an assumption. It stays available for
    someone who can confirm that assumption, it records `model_resolution` on
    every turn it touches, and it is never the default.
    """
    main = Path(path)
    if not main.is_file():
        raise FileNotFoundError("no such session file: {0}".format(main))

    rates = rates_data if rates_data is not None else _credits.load_rates()

    skills = SkillDetector()
    questions = QuestionDetector()

    timestamps: List[Any] = []
    malformed = 0
    tool_calls = 0
    agent_messages = 0
    models: List[str] = []
    cli_version: Optional[str] = None
    parent_thread_id: Optional[str] = None
    session_meta_lines = 0
    token_count_events = 0
    compaction_events = 0
    best: Optional[Dict[str, int]] = None
    best_total = -1

    # Turn state. Only `turn_context` opens a bucket - see the module docstring
    # for why `task_started` must not.
    turn_order: List[str] = []
    turns: Dict[str, Dict[str, Any]] = {}
    current_turn: Optional[str] = None
    synthetic_turns = 0

    per_request: List[Dict[str, Any]] = []
    per_request_dropped = 0
    previous_cumulative_total: Optional[int] = None
    reconciliation_holds = 0
    reconciliation_violations: List[Dict[str, Any]] = []

    context_windows: List[int] = []
    utilisation_samples: List[float] = []
    utilisation_measurable = 0

    parent_resolution: Optional[Dict[str, str]] = None
    parent_resolution_attempted = False

    def resolve_model(recorded: Optional[str]) -> Dict[str, Any]:
        """Apply the router-alias resolution order. Never guesses a model."""
        if not isinstance(recorded, str) or not recorded:
            return {"model": None, "recorded": recorded, "resolution": "absent-from-turn-context"}
        if not _credits.is_router_alias(recorded, rates):
            return {"model": recorded, "recorded": recorded, "resolution": "turn_context"}
        if infer_router_alias_model:
            for earlier in reversed(models):
                if not _credits.is_router_alias(earlier, rates):
                    return {
                        "model": earlier,
                        "recorded": recorded,
                        "resolution": "inferred-from-preceding-turn-context-in-file",
                    }
        if infer_router_alias_model and parent_thread_id:
            resolved = parent_resolution
            if resolved:
                return {
                    "model": resolved["model"],
                    "recorded": recorded,
                    "resolution": "inferred-from-parent-thread:{0}".format(
                        resolved["source_file"]
                    ),
                }
        return {"model": None, "recorded": recorded, "resolution": "unresolved-router-alias"}

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
            parent = payload.get("parent_thread_id")
            if isinstance(parent, str) and parent and not parent_thread_id:
                parent_thread_id = parent
            continue

        if kind == "compacted":
            compaction_events += 1
            continue

        if kind == "turn_context":
            recorded_model = payload.get("model")
            if (
                infer_router_alias_model
                and not parent_resolution_attempted
                and parent_thread_id
                and isinstance(recorded_model, str)
                and _credits.is_router_alias(recorded_model, rates)
            ):
                parent_resolution_attempted = True
                parent_resolution = _parent_thread_model(main, parent_thread_id, rates)
            resolution = resolve_model(recorded_model)
            if isinstance(recorded_model, str) and recorded_model and recorded_model not in models:
                models.append(recorded_model)

            turn_id = payload.get("turn_id")
            if not isinstance(turn_id, str) or not turn_id:
                synthetic_turns += 1
                turn_id = "unidentified-turn-{0:02d}".format(synthetic_turns)
            effort = payload.get("effort")
            if not isinstance(effort, str):
                collaboration = payload.get("collaboration_mode")
                if isinstance(collaboration, dict):
                    settings = collaboration.get("settings")
                    if isinstance(settings, dict):
                        candidate = settings.get("reasoning_effort")
                        effort = candidate if isinstance(candidate, str) else None
                else:
                    effort = None
            if turn_id not in turns:
                turn_order.append(turn_id)
                turns[turn_id] = {
                    "turn_id": turn_id,
                    "model": resolution["model"],
                    "model_as_recorded": resolution["recorded"],
                    "model_resolution": resolution["resolution"],
                    "effort": effort,
                    "requests": 0,
                    "credits_accumulated": 0.0,
                    "credits_priced": _credits.rate_for(resolution["model"], rates) is not None,
                    "tokens": dict((key, 0) for key in USAGE_DELTA_FIELDS),
                    "first_timestamp": moment,
                    "last_timestamp": moment,
                }
            else:
                turns[turn_id]["model"] = resolution["model"]
                turns[turn_id]["model_as_recorded"] = resolution["recorded"]
                turns[turn_id]["model_resolution"] = resolution["resolution"]
                turns[turn_id]["credits_priced"] = (
                    _credits.rate_for(resolution["model"], rates) is not None
                )
                if effort:
                    turns[turn_id]["effort"] = effort
            current_turn = turn_id
            continue

        if kind == "event_msg":
            event = payload.get("type")
            if event == "token_count":
                token_count_events += 1
                info = payload.get("info")
                if not isinstance(info, dict):
                    continue
                cumulative = info.get("total_token_usage")
                reported_delta = info.get("last_token_usage")
                window = info.get("model_context_window")
                if isinstance(window, int) and window > 0:
                    context_windows.append(window)

                if isinstance(cumulative, dict):
                    totals = _usage_dict(cumulative)
                    if totals["total_tokens"] > best_total:
                        best_total = totals["total_tokens"]
                        best = dict(totals)
                else:
                    totals = None

                has_reported_delta = isinstance(reported_delta, dict)
                if has_reported_delta:
                    delta = _usage_dict(reported_delta)
                    delta_source = "last_token_usage"
                elif totals is not None and previous_cumulative_total is not None:
                    # No per-request field on this build: fall back to the
                    # cumulative difference and say which channel was used.
                    delta = dict(
                        (key, max(totals[key] - _int((best or {}).get(key, 0)), 0))
                        for key in USAGE_DELTA_FIELDS
                    )
                    delta["total_tokens"] = max(
                        totals["total_tokens"] - previous_cumulative_total, 0
                    )
                    delta_source = "cumulative-difference"
                elif totals is not None:
                    delta = dict(totals)
                    delta_source = "first-cumulative-reading"
                else:
                    continue

                # The card's invariant. Counted, surfaced, never repaired.
                reconciles: Optional[bool] = None
                if (
                    has_reported_delta
                    and totals is not None
                    and previous_cumulative_total is not None
                ):
                    expected = totals["total_tokens"] - previous_cumulative_total
                    reconciles = expected == delta["total_tokens"]
                    if reconciles:
                        reconciliation_holds += 1
                    else:
                        reconciliation_violations.append(
                            {
                                "request_index": token_count_events,
                                "turn_id": current_turn,
                                "cumulative_difference": expected,
                                "reported_last_token_usage_total": delta["total_tokens"],
                                "compactions_seen_before_this_request": compaction_events,
                            }
                        )
                if totals is not None:
                    previous_cumulative_total = totals["total_tokens"]

                if has_reported_delta and isinstance(window, int) and window > 0:
                    utilisation_measurable += 1
                    utilisation_samples.append(delta["input_tokens"] / float(window))

                turn = turns.get(current_turn) if current_turn else None
                model_for_rate = turn["model"] if turn else None
                request_credits = _credits.credits_for_usage(
                    model_for_rate,
                    input_tokens=delta["input_tokens"],
                    cached_input_tokens=delta["cached_input_tokens"],
                    output_tokens=delta["output_tokens"],
                    rates=rates,
                )
                if turn is not None:
                    turn["requests"] += 1
                    for key in USAGE_DELTA_FIELDS:
                        turn["tokens"][key] += delta[key]
                    if request_credits is not None:
                        turn["credits_accumulated"] += request_credits
                    if moment is not None:
                        if turn["first_timestamp"] is None:
                            turn["first_timestamp"] = moment
                        turn["last_timestamp"] = moment

                if len(per_request) < MAX_PER_REQUEST_ENTRIES:
                    entry: Dict[str, Any] = {
                        "request_index": token_count_events,
                        "turn_id": current_turn,
                        "model": model_for_rate,
                        "timestamp": to_iso8601_z(moment),
                        "delta_source": delta_source,
                        "input_tokens": delta["input_tokens"],
                        "cached_input_tokens": delta["cached_input_tokens"],
                        "uncached_input_tokens": max(
                            delta["input_tokens"] - delta["cached_input_tokens"], 0
                        ),
                        "output_tokens": delta["output_tokens"],
                        "reasoning_output_tokens": delta["reasoning_output_tokens"],
                        "total_tokens": delta["total_tokens"],
                        "credits": request_credits,
                        "reconciles": reconciles,
                    }
                    if isinstance(window, int) and window > 0 and has_reported_delta:
                        entry["context_utilization"] = round(
                            delta["input_tokens"] / float(window), 6
                        )
                    per_request.append(entry)
                else:
                    per_request_dropped += 1
            elif event == "context_compacted":
                compaction_events += 1
            elif event == "agent_message":
                agent_messages += 1
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

    usage = best or dict((key, 0) for key in USAGE_DELTA_FIELDS)

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

    credits_block = _build_credits_block(
        turn_order=turn_order,
        turns=turns,
        per_request=per_request,
        per_request_dropped=per_request_dropped,
        token_count_events=token_count_events,
        reconciliation_holds=reconciliation_holds,
        reconciliation_violations=reconciliation_violations,
        compaction_events=compaction_events,
        rates=rates,
    )

    context_window = max(context_windows) if context_windows else None
    peak_utilisation = round(max(utilisation_samples), 6) if utilisation_samples else None

    cost = CostBlock(
        input_tokens=uncached_input,
        output_tokens=usage["output_tokens"],
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_write,
        estimated_usd=estimated,
        turns=len(turn_order),
        tool_calls=tool_calls,
        reasoning_output_tokens=usage["reasoning_output_tokens"],
        per_request=per_request,
        context_window=context_window,
        peak_context_utilization=peak_utilisation,
        credits=credits_block,
        model_requests=token_count_events,
    )

    parse_stats: Dict[str, Any] = {
        "host": HOST_NAME,
        "malformed_lines": malformed,
        "session_meta_lines": session_meta_lines,
        "token_count_events": token_count_events,
        "agent_messages": agent_messages,
        "turn_contexts": len(turn_order),
        "turn_attribution": (
            "every token_count event is attributed to the most recent turn_context; "
            "token_count carries no turn id of its own"
        ),
        "compaction_events": compaction_events,
        "token_usage_selection": "max(total_token_usage.total_tokens) across token_count events",
        "wall_clock_spans_multiple_sessions": session_meta_lines > 1,
        "reported_total_tokens": usage["total_tokens"],
        "reasoning_output_tokens_included_in_output": usage["reasoning_output_tokens"],
        "cache_write_semantics_unverified": cache_write == 0,
        "cache_write_ttl_assumed": cache_write_ttl or _default_cache_ttl(pricing_data),
        "pricing_checked_on": _pricing.checked_on(model, pricing_data),
        "unpriced_model": model if estimated is None and model else None,
        "context_window_observed": context_window,
        "context_utilization_samples": utilisation_measurable,
        "questions": questions.breakdown(),
        "skills": skills.breakdown(),
        "known_limits": [
            "no Skill tool in Codex; skill detection is shell-path only",
            "no AskUserQuestion equivalent; question count is heuristic only",
            "cache_write_input_tokens observed as 0 in every local session",
            "token_count events carry no turn id; turn attribution is positional",
            "no per-tool-call timing channel; skill call duration is not recoverable",
        ],
    }
    if not utilisation_samples:
        parse_stats["peak_context_utilization_unavailable_reason"] = (
            "Context utilisation needs both model_context_window and a per-request "
            "last_token_usage.input_tokens. This rollout supplied "
            "{0} usable pairs.".format(utilisation_measurable)
        )
    if synthetic_turns:
        parse_stats["turn_contexts_without_turn_id"] = synthetic_turns

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
        time=TimeBlock(
            agent_wall_clock_seconds=wall_clock,
            skill_call_timing_unavailable_reason=(
                "Codex rollouts record a tool call but not a tool result timestamp, so "
                "the duration of an individual skill call is not recoverable. The "
                "per-turn durations in cost.credits.per_turn are the finest timing "
                "this host supports."
            ),
        ),
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


def _build_credits_block(
    turn_order: List[str],
    turns: Dict[str, Dict[str, Any]],
    per_request: List[Dict[str, Any]],
    per_request_dropped: int,
    token_count_events: int,
    reconciliation_holds: int,
    reconciliation_violations: List[Dict[str, Any]],
    compaction_events: int,
    rates: Dict[str, Any],
) -> Dict[str, Any]:
    """Assemble the `cost.credits` sub-block.

    Everything here is derived: measured token deltas multiplied by the published
    rate card. The block therefore carries its own derivation statement, the rate
    card's URL and fetch date, the billing unit, and the two published
    multipliers the card records without a factor - because a credit figure that
    omits them is an understatement, not an estimate.
    """
    per_turn: List[Dict[str, Any]] = []
    priced_turn_credits: List[float] = []
    unpriced_models: Dict[str, str] = {}
    unresolved_alias_turns = 0
    by_model: Dict[str, Dict[str, Any]] = {}
    requests_all: List[int] = []
    requests_priced: List[int] = []

    for turn_id in turn_order:
        turn = turns[turn_id]
        model = turn["model"]
        priced = _credits.rate_for(model, rates) is not None
        first = turn.get("first_timestamp")
        last = turn.get("last_timestamp")
        duration = None
        if first is not None and last is not None:
            duration = round((last - first).total_seconds(), 3)
        entry: Dict[str, Any] = {
            "turn_id": turn_id,
            "model": model,
            "model_as_recorded": turn["model_as_recorded"],
            "model_resolution": turn["model_resolution"],
            "effort": turn["effort"],
            "model_requests": turn["requests"],
            "input_tokens": turn["tokens"]["input_tokens"],
            "cached_input_tokens": turn["tokens"]["cached_input_tokens"],
            "uncached_input_tokens": max(
                turn["tokens"]["input_tokens"] - turn["tokens"]["cached_input_tokens"], 0
            ),
            "output_tokens": turn["tokens"]["output_tokens"],
            "reasoning_output_tokens": turn["tokens"]["reasoning_output_tokens"],
            "total_tokens": turn["tokens"]["total_tokens"],
            "duration_seconds": duration,
        }
        requests_all.append(turn["requests"])
        if priced:
            entry["credits"] = round(turn["credits_accumulated"], 6)
            priced_turn_credits.append(turn["credits_accumulated"])
            requests_priced.append(turn["requests"])
            bucket = by_model.setdefault(
                model, {"turns": 0, "model_requests": 0, "credits": 0.0, "priced": True}
            )
            bucket["turns"] += 1
            bucket["model_requests"] += turn["requests"]
            bucket["credits"] = round(bucket["credits"] + turn["credits_accumulated"], 6)
        else:
            entry["credits"] = None
            recorded = turn["model_as_recorded"]
            reason = _credits.unpriced_reason(model, rates) or _credits.unpriced_reason(
                recorded, rates
            )
            if model is None:
                unresolved_alias_turns += 1
                entry["credits_unavailable_reason"] = (
                    reason
                    or "The turn's model could not be resolved, so no rate applies."
                )
            else:
                entry["credits_unavailable_reason"] = (
                    reason
                    or "{0} is not on the rate card in {1}.".format(
                        model, _credits.RATES_PATH.name
                    )
                )
            key = model or recorded or "unknown"
            unpriced_models[str(key)] = entry["credits_unavailable_reason"]
            bucket = by_model.setdefault(
                str(key), {"turns": 0, "model_requests": 0, "credits": None, "priced": False}
            )
            bucket["turns"] += 1
            bucket["model_requests"] += turn["requests"]
        per_turn.append(entry)

    priced_request_credits = [
        entry["credits"] for entry in per_request if isinstance(entry.get("credits"), (int, float))
    ]

    block: Dict[str, Any] = {
        "derived": True,
        "derivation": "measured token deltas from the rollout log x published credit rate card",
        "not_measured": (
            "Credits are not reported by Codex in the rollout log. This figure is "
            "computed here and is only as current as the rate card's fetch date."
        ),
        "billing_unit": _credits.BILLING_UNIT_TURN,
        "rate_card": _credits.source_block(rates),
        "token_semantics": _credits.token_semantics(rates),
        "turns_total": len(turn_order),
        "turns_priced": len(priced_turn_credits),
        "turns_unpriced": len(turn_order) - len(priced_turn_credits),
        "turns_with_unresolved_router_alias": unresolved_alias_turns,
        "model_requests": token_count_events,
        "per_turn": per_turn,
        "per_model": by_model,
        "unpriced_models": unpriced_models,
        "caveats": _credit_caveats(rates),
        "reference_measurement": _credits.billing_unit_note(rates).get("measured_2026_08_25"),
    }

    if priced_turn_credits:
        block["total"] = round(sum(priced_turn_credits), 6)
        block["per_turn_spread"] = _credits.spread(priced_turn_credits, _credits.BILLING_UNIT_TURN)
    else:
        block["total"] = None
        block["total_unavailable_reason"] = (
            "No turn in this session ran a model on the rate card, so there is no "
            "published rate to multiply the measured tokens by. "
            + (
                "Unpriced models seen: " + ", ".join(sorted(unpriced_models)) + "."
                if unpriced_models
                else "No turn_context recorded a model."
            )
        )
        block["per_turn_spread"] = None

    if block["turns_unpriced"] and priced_turn_credits:
        block["total_coverage"] = (
            "Covers {0} of {1} turns. The other {2} ran models with no published "
            "rate and are excluded rather than counted as zero.".format(
                len(priced_turn_credits), len(turn_order), block["turns_unpriced"]
            )
        )

    block["per_request_spread"] = _credits.spread(priced_request_credits, "request")
    if block["per_request_spread"] is not None:
        block["per_request_spread"]["comparison_warning"] = _credits.billing_unit_note(rates).get(
            "why"
        )

    block["requests_per_turn"] = _requests_per_turn(requests_all, requests_priced)

    if per_request_dropped:
        block["per_request_truncated"] = {
            "emitted": len(per_request),
            "dropped": per_request_dropped,
            "limit": MAX_PER_REQUEST_ENTRIES,
            "note": "Totals and spreads above cover only the emitted requests.",
        }

    rule = _credits.reconciliation_rule(rates)
    checked = reconciliation_holds + len(reconciliation_violations)
    block["reconciliation_invariant"] = {
        "rule": rule.get("rule"),
        "checked": checked,
        "holds": reconciliation_holds,
        "violates": len(reconciliation_violations),
        "rate": round(reconciliation_holds / checked, 6) if checked else None,
        "compaction_events_in_session": compaction_events,
        "on_violation": rule.get("on_violation"),
        "violations": reconciliation_violations,
        "reference": rule.get("measured_2026_08_25"),
    }
    if not checked:
        block["reconciliation_invariant"]["unavailable_reason"] = (
            "The invariant compares consecutive cumulative totals against the "
            "reported per-request delta. This rollout supplied fewer than two "
            "token_count events carrying last_token_usage."
        )
    return block


def _requests_per_turn(all_turns: List[int], priced_turns: List[int]) -> Dict[str, Any]:
    """Measured requests per turn, for this session, on both denominators.

    The rate card's corpus figure (median 5, mean 11.8) is measured over turns
    whose model is on the card. Both denominators are reported so the two are
    never read as the same number.
    """
    def describe(values: List[int]) -> Optional[Dict[str, Any]]:
        series = [value for value in values if value > 0]
        if not series:
            return None
        return {
            "n_turns": len(series),
            "median": _credits.percentile(series, 0.50),
            "mean": round(sum(series) / float(len(series)), 4),
            "max": max(series),
            "total_requests": sum(series),
        }

    return {
        "all_turns": describe(all_turns),
        "priced_turns_only": describe(priced_turns),
        "note": (
            "priced_turns_only is the denominator the rate card's reference "
            "measurement uses; all_turns includes turns on unpriced models."
        ),
    }


def _credit_caveats(rates: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Published multipliers with no factor on file, restated as what they do to the figure."""
    out: List[Dict[str, Any]] = []
    for entry in _credits.unquantified_multipliers(rates):
        out.append(
            {
                "name": entry.get("name"),
                "published": entry.get("published"),
                "factor": entry.get("factor"),
                "effect_on_this_figure": (
                    "Not applied, because no numeric factor is published. If this run "
                    "used it, the credit figure above is a floor rather than a total."
                ),
            }
        )
    return out


def _default_cache_ttl(pricing_data: Optional[Dict[str, Any]]) -> str:
    data = pricing_data if pricing_data is not None else _pricing.load_pricing()
    return data.get("cache_write_default_ttl", "5m")

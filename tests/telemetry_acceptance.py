#!/usr/bin/env python3
"""Validate the deterministic cost-and-time telemetry harness under evals/lib.

Run: python3 tests/telemetry_acceptance.py

Covers the traps that would silently corrupt a cost report:
  * usage summation, deduplicated per assistant message
  * the content-block line-split trap (one message, many JSONL lines, same usage)
  * the message.usage.iterations[] restatement trap
  * coefficient-of-variation maths and the consistency thresholds
  * the single-run case (CV undefined, never a fake 0.0)
  * the missing-baseline case (no invented human baseline, deltas null)
  * a malformed and a truncated JSONL line
  * pricing config integrity (every model carries a checked_on date)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.lib import aggregate, emit_summary  # noqa: E402
from evals.lib.telemetry import claude_code, codex, detect_host, parse_session  # noqa: E402
from evals.lib.telemetry import pricing as pricing_module  # noqa: E402
from evals.lib.telemetry.behavior import QuestionDetector, SkillDetector  # noqa: E402

REAL_CLAUDE_DIR = Path.home() / ".claude" / "projects" / "-Users-andrewfischer-Projects-ascent"
REAL_CODEX_DIR = Path.home() / ".codex" / "sessions"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# --------------------------------------------------------------------- fixtures


def assistant_line(message_id, usage, content, timestamp, request_id=None, uuid=None):
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "uuid": uuid or "{0}-{1}".format(message_id, len(content)),
        "requestId": request_id or "req_{0}".format(message_id),
        "version": "2.1.229",
        "isSidechain": False,
        "message": {"id": message_id, "model": "claude-opus-5", "usage": usage, "content": content},
    }


def usage(inp, out, read, create, iterations=1):
    block = {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_input_tokens": read,
        "cache_creation_input_tokens": create,
        "service_tier": "standard",
    }
    if iterations:
        # Real sessions restate the same figures here, once per inference iteration.
        block["iterations"] = [
            {
                "input_tokens": inp,
                "output_tokens": out,
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": create,
                "type": "message",
            }
        ] * iterations
    return block


def write_session(directory: Path, name: str, lines) -> Path:
    path = directory / name
    with path.open("w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(json.dumps(line) + "\n")
    return path


# ------------------------------------------------------------------------ tests


def test_usage_summation_and_line_split_trap(workspace: Path) -> None:
    """One message split across three lines must be counted once, not three times."""
    stamp = "2026-08-21T10:00:0{0}.000Z"
    lines = [
        # Message A: three JSONL lines, one per content block, identical usage.
        assistant_line("msg_A", usage(2, 100, 1000, 50), [{"type": "thinking", "thinking": "x"}], stamp.format(0), uuid="a1"),
        assistant_line("msg_A", usage(2, 100, 1000, 50), [{"type": "text", "text": "hello"}], stamp.format(1), uuid="a2"),
        assistant_line("msg_A", usage(2, 100, 1000, 50), [{"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {"command": "ls"}}], stamp.format(2), uuid="a3"),
        # Message B: a single line.
        assistant_line("msg_B", usage(3, 200, 2000, 60), [{"type": "tool_use", "id": "toolu_2", "name": "Read", "input": {}}], stamp.format(3), request_id="req_B", uuid="b1"),
    ]
    path = write_session(workspace, "split.jsonl", lines)
    result = claude_code.parse_session(path)

    check(result.cost.input_tokens == 5, "input_tokens should be 2+3=5, got {0}".format(result.cost.input_tokens))
    check(result.cost.output_tokens == 300, "output_tokens should be 300, got {0}".format(result.cost.output_tokens))
    check(result.cost.cache_read_tokens == 3000, "cache_read should be 3000, got {0}".format(result.cost.cache_read_tokens))
    check(result.cost.cache_creation_tokens == 110, "cache_creation should be 110, got {0}".format(result.cost.cache_creation_tokens))
    check(result.cost.total_tokens == 3415, "total should be 3415, got {0}".format(result.cost.total_tokens))
    check(result.cost.turns == 2, "two unique messages should be two turns, got {0}".format(result.cost.turns))
    check(result.cost.tool_calls == 2, "two distinct tool_use blocks, got {0}".format(result.cost.tool_calls))

    stats = result.parse_stats
    check(stats["assistant_lines"] == 4, "should have seen 4 assistant lines")
    check(stats["assistant_messages_deduplicated"] == 2, "should have deduplicated to 2 messages")
    check(stats["line_to_message_inflation_avoided"] == 2.0, "inflation factor should be 2.0")
    check(result.time.agent_wall_clock_seconds == 3.0, "wall clock should be first-to-last = 3s")


def test_iterations_are_never_double_counted(workspace: Path) -> None:
    """iterations[] restates the top-level figures; adding them would double the bill."""
    single = write_session(
        workspace,
        "iter_one.jsonl",
        [assistant_line("msg_1", usage(10, 20, 30, 40, iterations=1), [{"type": "text", "text": "a"}], "2026-08-21T10:00:00.000Z")],
    )
    triple = write_session(
        workspace,
        "iter_three.jsonl",
        [assistant_line("msg_1", usage(10, 20, 30, 40, iterations=3), [{"type": "text", "text": "a"}], "2026-08-21T10:00:00.000Z")],
    )
    one = claude_code.parse_session(single)
    three = claude_code.parse_session(triple)
    check(one.cost.total_tokens == 100, "expected 100 tokens, got {0}".format(one.cost.total_tokens))
    check(
        three.cost.total_tokens == one.cost.total_tokens,
        "three iterations must not change the total: {0} vs {1}".format(
            three.cost.total_tokens, one.cost.total_tokens
        ),
    )
    check(
        three.parse_stats["usage_iterations_entries_ignored"] == 3,
        "the ignored iteration entries should still be reported for auditability",
    )
    check(
        three.parse_stats["usage_iterations_tokens_not_double_counted"] == 300,
        "should report the 300 tokens it declined to add",
    )


def test_malformed_and_truncated_lines_do_not_crash(workspace: Path) -> None:
    """Real session files can end mid-write. The parser must survive that."""
    path = workspace / "broken.jsonl"
    good = assistant_line("msg_ok", usage(1, 2, 3, 4), [{"type": "text", "text": "fine"}], "2026-08-21T10:00:00.000Z")
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(good) + "\n")
        handle.write("this is not json at all\n")
        handle.write("[1, 2, 3]\n")                       # valid JSON, wrong shape
        handle.write("\n")                                 # blank line
        handle.write('{"type": "assistant", "message": ')  # truncated final line, no newline

    result = claude_code.parse_session(path)
    check(result.cost.total_tokens == 10, "the one good message should still be counted")
    check(
        result.parse_stats["malformed_lines"] == 3,
        "expected 3 unusable lines, got {0}".format(result.parse_stats["malformed_lines"]),
    )


def test_subagent_transcripts_are_included(workspace: Path) -> None:
    """Excluding subagents understates cost by roughly half on fan-out sessions."""
    main = write_session(
        workspace,
        "sess.jsonl",
        [assistant_line("msg_main", usage(1, 10, 100, 5), [{"type": "tool_use", "id": "toolu_a", "name": "Agent", "input": {}}], "2026-08-21T10:00:00.000Z")],
    )
    sub_dir = workspace / "sess" / "subagents"
    sub_dir.mkdir(parents=True)
    sub = write_session(
        sub_dir,
        "agent-abc.jsonl",
        [assistant_line("msg_sub", usage(2, 20, 200, 10), [{"type": "text", "text": "done"}], "2026-08-21T10:01:00.000Z")],
    )
    (sub_dir / "agent-abc.meta.json").write_text(
        json.dumps({"agentType": "general-purpose", "description": "do a thing"}), encoding="utf-8"
    )
    check(sub.is_file(), "fixture subagent transcript should exist")

    with_subs = claude_code.parse_session(main, include_subagents=True)
    without = claude_code.parse_session(main, include_subagents=False)
    check(with_subs.cost.total_tokens == 348, "expected 116+232=348, got {0}".format(with_subs.cost.total_tokens))
    check(without.cost.total_tokens == 116, "main-thread-only should be 116, got {0}".format(without.cost.total_tokens))
    check(with_subs.parse_stats["subagent_count"] == 1, "should have found one subagent")
    check(
        with_subs.parse_stats["subagents"][0]["agent_type"] == "general-purpose",
        "should read agentType out of the sidecar meta file",
    )
    check(
        with_subs.time.agent_wall_clock_seconds == 60.0,
        "wall clock should span the subagent's timestamps too",
    )


def test_behavior_detection() -> None:
    skills = SkillDetector()
    skills.observe_tool_use({"name": "Skill", "input": {"skill": "discover-project-context"}})
    skills.observe_tool_use({"name": "Skill", "input": {"skill": "superpowers:brainstorming"}})
    skills.observe_tool_use({"name": "Bash", "input": {"command": "python3 skills/retrieve-project-context/scripts/rank_context.py"}})
    skills.observe_tool_use({"name": "Bash", "input": {"command": "ls skills/"}})
    skills.observe_tool_use({"name": "Bash", "input": {"command": "mkdir -p docs/training/x-handoff"}})
    skills.observe_tool_use({"name": "Bash", "input": {"command": "cat > f.py <<'EOF'\nrefers to skills/ghost/run.py\nEOF"}})
    # Heredoc nested in a quoted string, the shape an agent produces when it
    # writes a file from inside `python3 -c`. The delimiter line carries trailing
    # quote/escape characters, so the terminator match must tolerate a boundary.
    skills.observe_tool_use({"name": "Bash", "input": {"command": 'python3 -c "open(1).write(\'\'\'<<EOF\\nsee skills/phantom/x.py\\nEOF\\", y\'\'\')"'}})
    # A real invocation after a heredoc body must still be found.
    skills.observe_tool_use({"name": "Bash", "input": {"command": "cat > f.py <<'EOF'\nuses skills/ghost/x.py\nEOF\npython3 skills/after-heredoc/run.py"}})
    invoked = skills.invoked()
    check("discover-project-context" in invoked, "Skill tool invocation should be detected")
    check("retrieve-project-context" in invoked, "bash-into-skills invocation should be detected")
    check("superpowers:brainstorming" in invoked, "plugin-scoped skill name should be recorded verbatim")
    check("brainstorming" in invoked, "bare alias of a plugin-scoped skill should also be recorded")
    check("ghost" not in invoked, "a skills path inside a heredoc body must not count as an invocation")
    check("phantom" not in invoked, "a heredoc nested in a quoted string must also be stripped")
    check("after-heredoc" in invoked, "a real invocation following a heredoc body must still be detected")
    check(not any(name.startswith("handoff") for name in invoked), "unrelated paths must not match")

    questions = QuestionDetector()
    questions.observe_tool_use({"name": "AskUserQuestion", "input": {"questions": [{"question": "Which scope?"}, {"question": "Which org?"}]}})
    questions.observe_text("Here is the plan. Should I proceed? See `what is this?` inline.")
    questions.observe_text("Subagent question?", from_subagent=True)
    questions.observe_tool_use({"name": "AskUserQuestion", "input": {"questions": [{"question": "Ignored?"}]}}, from_subagent=True)
    breakdown = questions.breakdown()
    check(breakdown["ask_user_question_tool"] == 2, "AskUserQuestion count should be exact (2)")
    check(breakdown["assistant_text_question_marks"] == 1, "inline code and subagent text must be excluded")
    check(questions.total() == 3, "total should be 2 structured + 1 heuristic")


def test_missing_skill_invocations_and_expectations(workspace: Path) -> None:
    path = write_session(
        workspace,
        "expect.jsonl",
        [assistant_line("msg_e", usage(1, 1, 1, 1), [{"type": "tool_use", "id": "toolu_s", "name": "Skill", "input": {"skill": "discover-project-context"}}], "2026-08-21T10:00:00.000Z")],
    )
    telemetry = claude_code.parse_session(path)
    record = telemetry.to_run_record(
        run_id="r1",
        suite_id="context-skills",
        arm="with-skills",
        skills_expected=["discover-project-context", "retrieve-project-context"],
    )
    behavior = record["behavior"]
    check(behavior["missing_skill_invocations"] == ["retrieve-project-context"],
          "should flag the expected-but-uninvoked skill, got {0}".format(behavior["missing_skill_invocations"]))


def test_no_invented_human_baseline(workspace: Path) -> None:
    """A baseline is recorded by a human or omitted. Never derived, never zero."""
    path = write_session(
        workspace,
        "baseline.jsonl",
        [
            assistant_line("m1", usage(1, 1, 1, 1), [{"type": "text", "text": "a"}], "2026-08-21T10:00:00.000Z"),
            assistant_line("m2", usage(1, 1, 1, 1), [{"type": "text", "text": "b"}], "2026-08-21T10:02:00.000Z"),
        ],
    )
    telemetry = claude_code.parse_session(path)
    bare = telemetry.to_run_record(run_id="r", suite_id="s", arm="with-skills")
    check("human_baseline_minutes" not in bare["time"], "no baseline given means no baseline key")
    check("time_saved_minutes" not in bare["time"], "no baseline means no time_saved_minutes, not zero")
    check("speedup_factor" not in bare["time"], "no baseline means no speedup_factor")
    check(bare["time"]["agent_wall_clock_seconds"] == 120.0, "wall clock should still be present")

    telemetry2 = claude_code.parse_session(path)
    with_baseline = telemetry2.to_run_record(
        run_id="r", suite_id="s", arm="with-skills",
        human_baseline_minutes=240, human_baseline_source="delivery-lead-estimate - 2026-08-21",
    )
    check(with_baseline["time"]["human_baseline_minutes"] == 240.0, "baseline should be carried through")
    check(with_baseline["time"]["time_saved_minutes"] == 238.0, "240 - 2 minutes = 238")
    check(with_baseline["time"]["speedup_factor"] == 120.0, "240/2 = 120x")


def test_cv_maths_and_thresholds() -> None:
    values = [10.0, 12.0, 14.0, 16.0, 18.0]
    cv = aggregate.coefficient_of_variation(values)
    # mean 14, sample stdev sqrt(10) = 3.1622776..., cv = 0.2258770...
    check(abs(cv - 0.22587697) < 1e-6, "CV of [10..18] should be 0.225877, got {0}".format(cv))
    check(aggregate.coefficient_of_variation([5.0]) is None, "one sample has no measurable spread")
    check(aggregate.coefficient_of_variation([]) is None, "empty series has no CV")
    check(aggregate.coefficient_of_variation([0.0, 0.0]) is None, "zero mean makes CV undefined")
    check(aggregate.coefficient_of_variation([7.0, 7.0, 7.0]) == 0.0, "identical runs genuinely have CV 0")

    check(aggregate.percentile([1, 2, 3, 4, 5], 0.5) == 3.0, "p50 of 1..5 is 3")
    check(abs(aggregate.percentile([1, 2, 3, 4, 5], 0.95) - 4.8) < 1e-9, "p95 of 1..5 interpolates to 4.8")
    check(aggregate.percentile([], 0.5) is None, "empty series has no percentile")

    check(aggregate.consistency_verdict([100, 100, 100]) == "predictable", "CV 0 over 3 runs is predictable")
    check(aggregate.consistency_verdict([100, 115, 130]) == "variable", "CV ~0.13 is variable")
    check(aggregate.consistency_verdict([50, 100, 200]) == "unpredictable", "CV ~0.76 is unpredictable")
    check(aggregate.consistency_verdict([100]) == "insufficient-runs", "one run supports no verdict")
    check(aggregate.consistency_verdict([100, 101]) == "insufficient-runs", "two runs support no verdict")


def _run_record(run_id, arm, total_tokens, usd, wall_seconds, outcome="pass", baseline=None):
    record = {
        "schema_version": aggregate.RUN_RECORD_SCHEMA,
        "run_id": run_id,
        "suite_id": "context-skills",
        "arm": arm,
        "correctness": {"outcome": outcome, "checks_total": 4, "checks_passed": 4 if outcome == "pass" else 2, "failed_check_ids": []},
        "cost": {
            "input_tokens": 10, "output_tokens": 20, "cache_read_tokens": 30, "cache_creation_tokens": 40,
            "total_tokens": total_tokens, "estimated_usd": usd, "turns": 3, "tool_calls": 5,
        },
        "time": {"agent_wall_clock_seconds": wall_seconds},
        "behavior": {"skills_invoked": [], "skills_expected": [], "missing_skill_invocations": [], "clarifying_questions_asked": 0, "clarifying_questions_required": []},
        "provenance": {"telemetry_source": "claude-code-session-jsonl", "session_path": "x", "extraction": "deterministic"},
    }
    if baseline is not None:
        record["time"]["human_baseline_minutes"] = baseline
        record["time"]["human_baseline_source"] = "delivery-lead-estimate - 2026-08-21"
    return record


def test_single_run_case() -> None:
    """One run: CV undefined, verdict insufficient-runs, never a fake 0.0."""
    summary = aggregate.build_summary("context-skills", [_run_record("r1", "with-skills", 50000, 0.4, 120.0)])
    arm = summary["arms"]["with-skills"]
    check(arm["runs"] == 1, "one run")
    check(arm["total_tokens"]["coefficient_of_variation"] is None,
          "CV must be null from one sample, not 0.0 - got {0!r}".format(arm["total_tokens"]["coefficient_of_variation"]))
    check(arm["wall_clock_seconds"]["coefficient_of_variation"] is None, "wall-clock CV must be null from one sample")
    check(arm["consistency_verdict"] == "insufficient-runs", "one run cannot be called predictable")
    check(arm["total_tokens"]["p50"] == 50000, "p50 of one run is that run")
    check(summary["consistency_thresholds"]["status"] == "provisional", "thresholds must be labelled provisional")


def test_missing_baseline_case() -> None:
    """No baseline arm: deltas is null, and the emitter says so instead of printing zeros."""
    records = [
        _run_record("r1", "with-skills", 50000, 0.40, 120.0),
        _run_record("r2", "with-skills", 51000, 0.41, 125.0),
        _run_record("r3", "with-skills", 52000, 0.42, 130.0),
    ]
    summary = aggregate.build_summary("context-skills", records)
    check(summary["deltas"] is None, "with no baseline arm, deltas must be null, not zeros")
    check(summary["arms"]["baseline-no-skills"]["runs"] == 0, "baseline arm should be present but empty")
    check(summary["arms"]["with-skills"]["consistency_verdict"] == "predictable", "3 tight runs are predictable")
    check(any("baseline" in note for note in summary.get("notes", [])), "the null deltas should be explained in notes")

    markdown = emit_summary.render(summary)
    check("is a measured saving" in markdown, "the emitter must state that nothing is a measured saving")
    check("human baseline" in markdown, "the emitter should say the human baseline is missing")
    check("0 minutes saved" not in markdown, "the emitter must never print a zero saving")
    check("Tokens saved" not in markdown, "with no baseline arm there is no tokens-saved line")
    check("Time saved" not in markdown, "with no baseline arm there is no time-saved line")

    with_baseline = aggregate.build_summary(
        "context-skills",
        records + [_run_record("b1", "baseline-no-skills", 400000, 3.60, 900.0, outcome="fail")],
    )
    check(with_baseline["deltas"] is not None, "a populated baseline arm should produce deltas")
    check(with_baseline["deltas"]["tokens_saved_p50"] == 349000, "400000 - 51000 = 349000")
    check(abs(with_baseline["deltas"]["usd_saved_p50"] - 3.19) < 1e-9, "3.60 - 0.41 = 3.19")
    check(with_baseline["deltas"]["correctness_pass_rate_delta"] == 1.0, "1.0 - 0.0 = 1.0")
    md2 = emit_summary.render(with_baseline)
    check("Tokens saved (median): 349,000" in md2, "the emitter should report the token delta")


def test_emitter_reports_recorded_baseline() -> None:
    records = [
        _run_record("r1", "with-skills", 50000, 0.40, 120.0, baseline=240),
        _run_record("r2", "with-skills", 51000, 0.41, 125.0, baseline=240),
        _run_record("r3", "with-skills", 52000, 0.42, 130.0, baseline=240),
    ]
    summary = aggregate.build_summary("context-skills", records)
    arm = summary["arms"]["with-skills"]
    check(arm["human_baseline_minutes"] == 240.0, "a consistently recorded baseline should surface on the arm")
    check(abs(arm["time_saved_minutes_p50"] - 237.92) < 0.01, "240 - 125/60 minutes")
    markdown = emit_summary.render(summary)
    check("human baseline 4h" in markdown, "the emitter should print the recorded baseline")
    check("saved" in markdown, "the emitter should print the saving")

    disagreeing = aggregate.build_summary(
        "context-skills",
        [
            _run_record("r1", "with-skills", 50000, 0.40, 120.0, baseline=240),
            _run_record("r2", "with-skills", 51000, 0.41, 125.0, baseline=90),
            _run_record("r3", "with-skills", 52000, 0.42, 130.0, baseline=240),
        ],
    )
    check(
        "human_baseline_minutes" not in disagreeing["arms"]["with-skills"],
        "disagreeing recorded baselines must not be averaged into a single figure",
    )


def test_no_emoji_or_adjectives_in_emitter() -> None:
    summary = aggregate.build_summary("context-skills", [_run_record("r1", "with-skills", 50000, 0.4, 120.0, baseline=240)])
    markdown = emit_summary.render(summary)
    check(all(ord(ch) < 0x2190 for ch in markdown), "the emitted block must contain no emoji or symbol glyphs")
    for banned in ("excellent", "great", "impressive", "amazing", "dramatic", "huge"):
        check(banned not in markdown.lower(), "the emitted block must not contain the adjective {0!r}".format(banned))


def test_pricing_config_integrity() -> None:
    data = pricing_module.load_pricing(reload=True)
    check(data["schema_version"] == "ascent.eval-pricing.v1", "pricing schema version")
    check("claude-api" in json.dumps(data["provenance"]), "provenance must credit the claude-api skill")
    for name, entry in data["models"].items():
        check(bool(entry.get("checked_on")), "model {0} is missing a checked_on date".format(name))
        rates = entry["usd_per_million"]
        for field in ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h"):
            check(field in rates, "model {0} is missing the {1} rate".format(name, field))
        check(rates["cache_read"] < rates["input"], "cache reads must be cheaper than fresh input for {0}".format(name))
        check(rates["cache_write_5m"] > rates["input"], "cache writes carry a premium for {0}".format(name))
        check(rates["cache_write_1h"] > rates["cache_write_5m"], "1h cache writes cost more than 5m for {0}".format(name))

    check(pricing_module.normalise_model("claude-opus-5[1m]") == "claude-opus-5", "the [1m] suffix should resolve")
    check(pricing_module.normalise_model("anthropic.claude-opus-5") == "claude-opus-5", "the Bedrock prefix should resolve")
    check(pricing_module.rate_for("no-such-model") is None, "an unknown model must return None, not a default")
    check(pricing_module.price_usage("no-such-model", 1000, 1000) is None, "unknown models must price as None, never 0.0")

    priced = pricing_module.price_usage("claude-opus-5", input_tokens=1_000_000, output_tokens=0)
    check(abs(priced - 5.0) < 1e-9, "1M input tokens on opus-5 should be $5.00, got {0}".format(priced))
    priced = pricing_module.price_usage("claude-opus-5", cache_read_tokens=1_000_000)
    check(abs(priced - 0.5) < 1e-9, "1M cache-read tokens should be $0.50, got {0}".format(priced))
    five_min = pricing_module.price_usage("claude-opus-5", cache_creation_tokens=1_000_000, cache_write_ttl="5m")
    one_hour = pricing_module.price_usage("claude-opus-5", cache_creation_tokens=1_000_000, cache_write_ttl="1h")
    check(abs(five_min - 6.25) < 1e-9, "5m cache write should be $6.25, got {0}".format(five_min))
    check(abs(one_hour - 10.0) < 1e-9, "1h cache write should be $10.00, got {0}".format(one_hour))

    source = (ROOT / "evals" / "lib" / "telemetry" / "pricing.py").read_text(encoding="utf-8")
    for literal in ("5.0", "25.0", "3.0", "15.0"):
        check(
            "= {0}".format(literal) not in source,
            "pricing.py must not hardcode the rate literal {0}".format(literal),
        )


def test_codex_token_arithmetic(workspace: Path) -> None:
    """Codex's cached_input_tokens is a subset of input_tokens; ours is not."""
    path = workspace / "rollout-fixture.jsonl"
    lines = [
        {"timestamp": "2026-08-21T10:00:00.000Z", "type": "session_meta", "payload": {"session_id": "s1", "cwd": "/tmp", "cli_version": "0.148.0"}},
        {"timestamp": "2026-08-21T10:00:01.000Z", "type": "turn_context", "payload": {"model": "gpt-5.6-terra", "effort": "high"}},
        {"timestamp": "2026-08-21T10:00:02.000Z", "type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec", "input": "python3 skills/discover-project-context/scripts/x.py"}},
        {"timestamp": "2026-08-21T10:00:03.000Z", "type": "event_msg", "payload": {"type": "agent_message", "message": "Done. Want me to continue?"}},
        {"timestamp": "2026-08-21T10:00:04.000Z", "type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 16184, "cached_input_tokens": 4864, "cache_write_input_tokens": 0, "output_tokens": 144, "reasoning_output_tokens": 78, "total_tokens": 16328}}}},
        {"timestamp": "2026-08-21T10:00:05.000Z", "type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 33256, "cached_input_tokens": 19968, "cache_write_input_tokens": 0, "output_tokens": 239, "reasoning_output_tokens": 111, "total_tokens": 33495}}}},
    ]
    with path.open("w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(json.dumps(line) + "\n")
        handle.write('{"timestamp": "2026-08-21T10:00:06.000Z", "type": "event')  # truncated tail

    result = codex.parse_session(path)
    check(result.cost.cache_read_tokens == 19968, "cache_read should be cached_input_tokens (19968)")
    check(result.cost.input_tokens == 33256 - 19968, "uncached input should be input minus cached")
    check(result.cost.output_tokens == 239, "output should be reported as-is (reasoning is a subset)")
    check(
        result.cost.total_tokens == 33495,
        "our total must equal Codex's own total_tokens (33495), got {0}".format(result.cost.total_tokens),
    )
    check(result.cost.estimated_usd is None, "gpt-5.6-terra has no rate on file, so usd must be None")
    check(result.parse_stats["unpriced_model"] == "gpt-5.6-terra", "the unpriced model should be named")
    check(result.parse_stats["malformed_lines"] == 1, "the truncated tail should be counted, not fatal")
    check(result.cost.tool_calls == 1, "the custom_tool_call should count as a tool call")
    check("discover-project-context" in result.behavior.skills_invoked, "a shell path into skills/ should be detected")
    check(result.behavior.clarifying_questions_asked == 1, "the agent_message question mark should be counted")
    check(result.parse_stats["cache_write_semantics_unverified"] is True, "the unverified cache-write assumption must be flagged")
    check(result.host_version == "0.148.0", "cli_version should be read as the host version")
    check(detect_host(path) == "codex", "a rollout file should be detected as codex")


def test_cli_contracts(workspace: Path) -> None:
    session = write_session(
        workspace,
        "cli.jsonl",
        [assistant_line("m1", usage(1, 10, 100, 5), [{"type": "text", "text": "x"}], "2026-08-21T10:00:00.000Z")],
    )
    out = workspace / "record.json"
    proc = subprocess.run(
        [sys.executable, "-m", "evals.lib.telemetry", "--session", str(session),
         "--suite", "context-skills", "--arm", "with-skills", "--run-id", "cli-1", "--out", str(out)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    check(proc.returncode == 0, "telemetry CLI should exit 0: {0}".format(proc.stderr))
    check(proc.stdout == "", "with --out, stdout must stay empty; got {0!r}".format(proc.stdout))
    record = json.loads(out.read_text(encoding="utf-8"))
    check(record["schema_version"] == "ascent.eval-run-record.v1", "CLI must emit the run-record schema version")
    check(record["run_id"] == "cli-1", "run id should be honoured")

    stdout_proc = subprocess.run(
        [sys.executable, "-m", "evals.lib.telemetry", "--session", str(session), "--suite", "s"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    check(stdout_proc.returncode == 0, "telemetry CLI without --out should exit 0")
    check(json.loads(stdout_proc.stdout)["schema_version"] == "ascent.eval-run-record.v1",
          "without --out the run record must go to stdout as JSON")

    missing = subprocess.run(
        [sys.executable, "-m", "evals.lib.telemetry", "--session", str(workspace / "nope.jsonl")],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    check(missing.returncode == 2, "a missing session file should exit 2, got {0}".format(missing.returncode))

    runs = workspace / "runs"
    runs.mkdir()
    (runs / "a.json").write_text(json.dumps(_run_record("a", "with-skills", 1000, 0.1, 10.0)), encoding="utf-8")
    (runs / "b.json").write_text(json.dumps(_run_record("b", "with-skills", 1100, 0.11, 11.0)), encoding="utf-8")
    (runs / "junk.json").write_text("{}", encoding="utf-8")
    (runs / "broken.json").write_text("not json", encoding="utf-8")

    agg = subprocess.run(
        [sys.executable, "-m", "evals.lib.aggregate", "--suite", "context-skills",
         "--runs-dir", str(runs), "--out", "-"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    check(agg.returncode == 0, "aggregate CLI should exit 0: {0}".format(agg.stderr))
    summary = json.loads(agg.stdout)
    check(summary["arms"]["with-skills"]["runs"] == 2, "non-run-record files must be skipped, not counted")
    check("skipping" in agg.stderr, "skipped files should be reported on stderr")

    summary_path = workspace / "latest.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    emit = subprocess.run(
        [sys.executable, "-m", "evals.lib.emit_summary", "--summary", str(summary_path)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    check(emit.returncode == 0, "emit_summary CLI should exit 0: {0}".format(emit.stderr))
    check("Evaluation: context-skills" in emit.stdout, "emitter should name the suite")

    bad_summary = workspace / "bad.json"
    bad_summary.write_text(json.dumps({"schema_version": "something-else"}), encoding="utf-8")
    bad = subprocess.run(
        [sys.executable, "-m", "evals.lib.emit_summary", "--summary", str(bad_summary)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    check(bad.returncode == 2, "a wrong schema version should exit 2, got {0}".format(bad.returncode))


def test_real_session_files() -> None:
    """Smoke test against real logs on this machine. Skipped when absent."""
    claude_files = sorted(REAL_CLAUDE_DIR.glob("*.jsonl")) if REAL_CLAUDE_DIR.is_dir() else []
    if not claude_files:
        sys.stderr.write("note: no real Claude Code sessions found; skipping that smoke test\n")
    for path in claude_files:
        result = parse_session(path)
        check(result.host_name == "claude-code", "{0} should parse as claude-code".format(path.name))
        check(result.cost.total_tokens > 0, "{0} should report tokens".format(path.name))
        check(result.cost.turns > 0, "{0} should report turns".format(path.name))
        check(result.cost.estimated_usd is not None, "{0} model should be priced".format(path.name))
        inflation = result.parse_stats["line_to_message_inflation_avoided"]
        check(inflation is not None and inflation >= 1.0,
              "{0} inflation factor should be >= 1.0, got {1}".format(path.name, inflation))
        without = claude_code.parse_session(path, include_subagents=False)
        check(without.cost.total_tokens <= result.cost.total_tokens,
              "excluding subagents can only lower the total for {0}".format(path.name))

    codex_files = sorted(REAL_CODEX_DIR.glob("**/*.jsonl")) if REAL_CODEX_DIR.is_dir() else []
    if not codex_files:
        sys.stderr.write("note: no real Codex rollouts found; skipping that smoke test\n")
    for path in codex_files:
        result = parse_session(path)
        check(result.host_name == "codex", "{0} should parse as codex".format(path.name))
        check(result.cost.input_tokens >= 0, "{0} must not produce negative uncached input".format(path.name))
        reported = result.parse_stats["reported_total_tokens"]
        if reported:
            check(result.cost.total_tokens == reported,
                  "{0}: our total {1} must match Codex's {2}".format(path.name, result.cost.total_tokens, reported))


def test_reporting_surfaces() -> None:
    """The deck and workbench are this rail's surfaces; assert their contract here.

    Moved out of tests/skill_evals_acceptance.py so the determinism rail owns no
    docs/ file. Assertions are structural, never counts of a specific slide.
    """
    presentation = (ROOT / "docs" / "sgaf-717-evals-presentation.html").read_text(encoding="utf-8")
    slide_count = presentation.count('class="slide')
    check(slide_count >= 9, f"working presentation should retain at least nine slides, found {slide_count}")
    check(
        presentation.count("data-note=") == slide_count,
        f"every slide should carry a presenter note: {slide_count} slides, {presentation.count('data-note=')} notes",
    )
    for expected in ("ArrowRight", "progressBar", "notesButton"):
        check(expected in presentation, f"presentation navigation is missing {expected}")
    workbench = (ROOT / "docs" / "evals-workbench.html").read_text(encoding="utf-8")
    server = (ROOT / "docs" / "evals_workbench.py").read_text(encoding="utf-8")
    for expected in ("/api/run/", "/api/summary/", "/api/runs/", "Run evaluation"):
        check(expected in workbench, f"workbench is missing {expected}")
    for question in ("Did it do the job right", "What did it cost", "How much time did it save"):
        check(question in workbench, f"workbench does not lead with the question: {question}")
    for expected in ('SUITE_ID = "context-skills"', "RUN_LOCK", "RUN_TIMEOUT_SECONDS = 90"):
        check(expected in server, f"workbench server is missing its execution boundary: {expected}")
    check(
        "shell=True" not in server and "shlex" not in server,
        "workbench server must not build a shell command from input",
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ascent-telemetry-test-") as temp:
        workspace = Path(temp)
        test_usage_summation_and_line_split_trap(workspace)
        test_iterations_are_never_double_counted(workspace)
        test_malformed_and_truncated_lines_do_not_crash(workspace)
        test_subagent_transcripts_are_included(workspace)
        test_behavior_detection()
        test_missing_skill_invocations_and_expectations(workspace)
        test_no_invented_human_baseline(workspace)
        test_cv_maths_and_thresholds()
        test_single_run_case()
        test_missing_baseline_case()
        test_emitter_reports_recorded_baseline()
        test_no_emoji_or_adjectives_in_emitter()
        test_pricing_config_integrity()
        test_codex_token_arithmetic(workspace)
        test_cli_contracts(workspace)
        test_real_session_files()
        test_reporting_surfaces()
        ran = [name for name in globals() if name.startswith("test_")]
    print(json.dumps({"suite": "telemetry-acceptance", "outcome": "pass",
                      "checks": len(ran)}))


if __name__ == "__main__":
    main()

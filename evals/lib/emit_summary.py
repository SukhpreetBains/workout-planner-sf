"""Render a suite summary as a paste-ready markdown block for Jira or a PR body.

    python3 -m evals.lib.emit_summary --suite context-skills
    python3 -m evals.lib.emit_summary --summary evals/<suite>/results/latest.json

Per the spec's "Emitting the result into the workflow": deliverable, correctness
verdict, tokens, cost, agent time, human baseline, time saved, consistency
verdict. Facts only - no adjectives, no emoji.

The two rules that keep this honest:

  * A line is omitted entirely when the underlying fact was not recorded. No
    human baseline means no baseline line and no time-saved line - not "0 minutes
    saved", which reads as a measurement.
  * The reader is a consultant or a delivery lead, so the three questions lead in
    the spec's words, with the standard term in parentheses once.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .aggregate import (
    BASELINE,
    SUITE_SUMMARY_SCHEMA,
    VERDICT_INSUFFICIENT,
    VERDICT_NO_COST_DATA,
    WITH_SKILLS,
    suite_dir,
)

VERDICT_PLAIN = {
    "predictable": "predictable - cost per run is safe to quote",
    "variable": "variable - budget with headroom",
    "unpredictable": "unpredictable - do not quote a per-run cost",
    VERDICT_INSUFFICIENT: "not enough runs to say",
    VERDICT_NO_COST_DATA: "no cost was recorded, so there is nothing to compare",
}

ARM_LABEL = {
    WITH_SKILLS: "with Ascent skills",
    BASELINE: "no skills (baseline)",
}


def _fmt_int(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return "{0:,}".format(int(round(value)))


def _fmt_usd(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return "${0:,.2f}".format(value) if abs(value) >= 0.01 else "${0:.4f}".format(value)


def _fmt_duration(seconds: Optional[float]) -> Optional[str]:
    if seconds is None:
        return None
    total = int(round(seconds))
    if total < 60:
        return "{0}s".format(total)
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return "{0}m {1}s".format(minutes, secs)
    hours, minutes = divmod(minutes, 60)
    return "{0}h {1}m".format(hours, minutes)


def _fmt_minutes(minutes: Optional[float]) -> Optional[str]:
    if minutes is None:
        return None
    if abs(minutes) >= 60:
        hours = minutes / 60.0
        return "{0:g}h".format(round(hours, 1))
    return "{0:g}m".format(round(minutes, 1))


def _pass_line(arm: Dict[str, Any]) -> str:
    rate = arm.get("correctness_pass_rate")
    runs = arm.get("runs") or 0
    if rate is None:
        return "not recorded ({0} run{1})".format(runs, "" if runs == 1 else "s")
    passed = int(round(rate * runs))
    return "{0}/{1} runs passed".format(passed, runs)


def render(summary: Dict[str, Any]) -> str:
    """Render an ascent.eval-suite-summary.v1 document as markdown."""
    if summary.get("schema_version") != SUITE_SUMMARY_SCHEMA:
        raise ValueError(
            "expected schema_version {0!r}, got {1!r}".format(
                SUITE_SUMMARY_SCHEMA, summary.get("schema_version")
            )
        )

    arms = summary.get("arms") or {}
    treated = arms.get(WITH_SKILLS) or {}
    control = arms.get(BASELINE) or {}
    deltas = summary.get("deltas")

    lines: List[str] = []
    lines.append("**Evaluation: {0}**".format(summary.get("suite_id", "unknown")))
    runs = treated.get("runs") or 0
    lines.append(
        "Runs: {0} with skills, {1} baseline. Generated {2}.".format(
            runs, control.get("runs") or 0, summary.get("generated_at", "unknown")
        )
    )
    lines.append("")

    lines.append("| Question | Result |")
    lines.append("| --- | --- |")
    lines.append("| Did it do the job right? | {0} |".format(_pass_line(treated)))

    tokens = treated.get("total_tokens") or {}
    usd = treated.get("estimated_usd") or {}
    token_p50 = _fmt_int(tokens.get("p50"))
    usd_p50 = _fmt_usd(usd.get("p50"))
    credits_block = treated.get("credits") or {}
    credits_p50 = credits_block.get("p50")
    cost_cell_parts = []
    if token_p50:
        cost_cell_parts.append("{0} tokens (median run)".format(token_p50))
    if usd_p50:
        cost_cell_parts.append(usd_p50)
    if isinstance(credits_p50, (int, float)) and not isinstance(credits_p50, bool):
        # Calvin's unit: "is it 70 credits one time and 40 credits another time?"
        cost_cell_parts.append("{0:,.1f} credits (derived)".format(credits_p50))
    lines.append(
        "| What did it cost? | {0} |".format(
            ", ".join(cost_cell_parts) if cost_cell_parts else "not recorded"
        )
    )

    cv = tokens.get("coefficient_of_variation")
    verdict = treated.get("consistency_verdict") or VERDICT_INSUFFICIENT
    if cv is None:
        cost_spread = "how much the cost jumps around: {0}".format(VERDICT_PLAIN.get(verdict, verdict))
    else:
        cost_spread = "{0} to {1} tokens across runs; how much the cost jumps around (coefficient of variation) {2:.2f} - {3}".format(
            _fmt_int(tokens.get("min")),
            _fmt_int(tokens.get("max")),
            cv,
            VERDICT_PLAIN.get(verdict, verdict),
        )
    lines.append("| Was that predictable? | {0} |".format(cost_spread))

    credits_cv = credits_block.get("coefficient_of_variation")
    if isinstance(credits_cv, (int, float)) and not isinstance(credits_cv, bool):
        credits_verdict = treated.get("credits_consistency_verdict") or VERDICT_INSUFFICIENT
        lines.append(
            "| Predictable in credits? | {0} to {1} credits across runs; {2:.2f} - {3} |".format(
                "{0:,.1f}".format(credits_block.get("min") or 0.0),
                "{0:,.1f}".format(credits_block.get("max") or 0.0),
                credits_cv,
                VERDICT_PLAIN.get(credits_verdict, credits_verdict),
            )
        )

    wall = treated.get("wall_clock_seconds") or {}
    agent_time = _fmt_duration(wall.get("p50"))
    baseline_minutes = treated.get("human_baseline_minutes")
    saved = treated.get("time_saved_minutes_p50")
    if agent_time and baseline_minutes is not None and saved is not None:
        time_cell = "agent {0} vs human baseline {1}; {2} saved".format(
            agent_time, _fmt_minutes(baseline_minutes), _fmt_minutes(saved)
        )
    elif agent_time:
        time_cell = "agent {0}; no human baseline recorded, so time saved is unknown".format(
            agent_time
        )
    else:
        time_cell = "not recorded"
    lines.append("| How much time did it save? | {0} |".format(time_cell))

    if deltas:
        lines.append("")
        lines.append("**Versus the same task with no skills**")
        for label, value in (
            ("Tokens saved (median)", _fmt_int(deltas.get("tokens_saved_p50"))),
            ("Cost saved (median)", _fmt_usd(deltas.get("usd_saved_p50"))),
            (
                "Credits saved (median, derived)",
                None
                if deltas.get("credits_saved_p50") is None
                else "{0:,.1f}".format(deltas["credits_saved_p50"]),
            ),
            ("Time saved (median)", _fmt_minutes(deltas.get("minutes_saved_p50"))),
        ):
            if value is not None:
                lines.append("- {0}: {1}".format(label, value))
        pass_delta = deltas.get("correctness_pass_rate_delta")
        if pass_delta is not None:
            lines.append(
                "- Correctness: {0:+.0%} pass rate versus baseline".format(pass_delta)
            )
        improvement = deltas.get("consistency_improvement")
        if improvement:
            lines.append("- Consistency: {0}".format(improvement))
    else:
        lines.append("")
        lines.append(
            "No baseline-no-skills arm has been run, so no figure here is a measured "
            "saving."
        )

    if baseline_minutes is not None:
        source = treated.get("human_baseline_source")
        if source:
            lines.append("")
            lines.append("Human baseline source: {0}".format(source))

    skill_seconds = treated.get("skill_call_seconds") or {}
    if skill_seconds:
        lines.append("")
        lines.append("**Skill calls**")
        for skill in sorted(skill_seconds):
            entry = skill_seconds[skill]
            lines.append(
                "- {0}: {1} calls, {2:.1f}s total".format(
                    skill, entry.get("calls", 0), float(entry.get("total_seconds") or 0.0)
                )
                + (" ({0})".format(entry["reading"]) if entry.get("reading") else "")
            )

    reconciliation = treated.get("token_reconciliation")
    if isinstance(reconciliation, dict) and reconciliation.get("violates"):
        lines.append("")
        lines.append(
            "Token reconciliation: {0} of {1} per-request deltas did not reconcile "
            "against the cumulative counter. Not repaired; see the run records."
            .format(reconciliation["violates"], reconciliation.get("checked"))
        )

    lines.append("")
    if credits_block.get("p50") is not None:
        lines.append(
            "Credits are derived, not reported: measured tokens times the published "
            "rate card. Published multipliers for fast mode and image generation have "
            "no numeric factor on file and are not applied, so a credit figure here is "
            "a floor."
        )
    lines.append(
        "Consistency thresholds are provisional. Telemetry is extracted from session "
        "logs by code; no model reads a transcript to produce these numbers."
    )
    return "\n".join(lines)


def load_summary(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m evals.lib.emit_summary",
        description="Render a suite summary as a paste-ready markdown block.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--suite", help="suite id; reads evals/<suite>/results/latest.json")
    group.add_argument("--summary", help="path to a suite-summary JSON file")
    parser.add_argument("--out", help="write markdown here (default: stdout)")
    parser.add_argument("--root", help="repository root, for use outside a checkout")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser() if args.root else None

    if args.summary:
        path = Path(args.summary).expanduser()
    else:
        path = suite_dir(args.suite, root) / "results" / "latest.json"

    if not path.is_file():
        sys.stderr.write("error: no such summary file: {0}\n".format(path))
        return 2
    try:
        summary = load_summary(path)
    except ValueError as exc:
        sys.stderr.write("error: summary is not valid JSON: {0}\n".format(exc))
        return 2

    try:
        markdown = render(summary)
    except ValueError as exc:
        sys.stderr.write("error: {0}\n".format(exc))
        return 2

    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown + "\n", encoding="utf-8")
        sys.stderr.write("wrote {0}\n".format(out_path))
    else:
        sys.stdout.write(markdown + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

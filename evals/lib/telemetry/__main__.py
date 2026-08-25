"""CLI: turn one agent session log into an ascent.eval-run-record.v1 file.

    python3 -m evals.lib.telemetry --session <path> --out <run-record.json>

Stable interface for other tooling to shell out to. Contract:

  * Exit 0 on a successful parse, 2 on a usage or IO error.
  * With `--out`, the run record is written there and a one-line human summary
    goes to stderr; stdout stays empty so the file is the only product.
  * Without `--out`, the run record is written to stdout as JSON, so callers can
    pipe it. Nothing else is ever written to stdout.
  * `--host` is optional; the host is detected from the file's own shape.

Flags that supply what a parser cannot know deterministically:

  --human-baseline-minutes / --human-baseline-source
        Recorded by a human. Omit both and the `time` block carries wall clock
        only - never a fabricated baseline.
  --correctness <path>
        A JSON file holding the `correctness` block from the correctness runner.
  --skills-expected / --questions-required
        Repeatable expectations, so `missing_skill_invocations` can be computed.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import HOSTS, detect_host, parse_session


def _default_run_id(suite_id: str, arm: str) -> str:
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = "01" if arm == "with-skills" else "b1"
    return "{0}-{1}-{2}".format(suite_id, stamp, suffix)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m evals.lib.telemetry",
        description="Parse an agent session log into an ascent.eval-run-record.v1 file.",
    )
    parser.add_argument("--session", required=True, help="path to the session log")
    parser.add_argument("--out", help="write the run record here (default: stdout)")
    parser.add_argument(
        "--host",
        choices=sorted(HOSTS),
        help="session host; detected from the file when omitted",
    )
    parser.add_argument("--suite", default="unknown", help="suite id for the run record")
    parser.add_argument(
        "--arm",
        default="with-skills",
        choices=["with-skills", "baseline-no-skills"],
        help="comparison arm this run belongs to",
    )
    parser.add_argument("--run-id", help="run id (default: <suite>-<utc-timestamp>-<n>)")
    parser.add_argument(
        "--correctness",
        help="path to a JSON file holding the correctness block",
    )
    parser.add_argument(
        "--human-baseline-minutes",
        type=float,
        help="human baseline in minutes, as recorded by a human. Never invented.",
    )
    parser.add_argument(
        "--human-baseline-source",
        help="who recorded the baseline and when, e.g. 'delivery-lead-estimate - 2026-08-21'",
    )
    parser.add_argument(
        "--skills-expected",
        action="append",
        default=[],
        metavar="SKILL",
        help="repeatable: a skill this run was expected to invoke",
    )
    parser.add_argument(
        "--questions-required",
        action="append",
        default=[],
        metavar="QUESTION",
        help="repeatable: a clarifying question this run was expected to ask",
    )
    parser.add_argument(
        "--no-subagents",
        action="store_true",
        help="exclude subagent transcripts (understates cost; default is to include)",
    )
    parser.add_argument(
        "--cache-write-ttl",
        choices=["5m", "1h"],
        default="5m",
        help="cache-write TTL to price at; logs do not record it (default 5m)",
    )
    parser.add_argument(
        "--print-detection",
        action="store_true",
        help="also write the parse_stats detection detail to stderr",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    session = Path(args.session).expanduser()
    if not session.is_file():
        sys.stderr.write("error: no such session file: {0}\n".format(session))
        return 2

    try:
        host = args.host or detect_host(session)
    except ValueError as exc:
        sys.stderr.write("error: {0}\n".format(exc))
        return 2

    correctness = None
    if args.correctness:
        correctness_path = Path(args.correctness).expanduser()
        if not correctness_path.is_file():
            sys.stderr.write("error: no such correctness file: {0}\n".format(correctness_path))
            return 2
        try:
            with correctness_path.open("r", encoding="utf-8") as handle:
                correctness = json.load(handle)
        except ValueError as exc:
            sys.stderr.write("error: correctness file is not valid JSON: {0}\n".format(exc))
            return 2

    try:
        telemetry = parse_session(
            session,
            host=host,
            include_subagents=not args.no_subagents,
            cache_write_ttl=args.cache_write_ttl,
        )
    except (OSError, ValueError) as exc:
        sys.stderr.write("error: could not parse session: {0}\n".format(exc))
        return 2

    record = telemetry.to_run_record(
        run_id=args.run_id or _default_run_id(args.suite, args.arm),
        suite_id=args.suite,
        arm=args.arm,
        correctness=correctness,
        human_baseline_minutes=args.human_baseline_minutes,
        human_baseline_source=args.human_baseline_source,
        skills_expected=args.skills_expected or None,
        clarifying_questions_required=args.questions_required or None,
    )

    payload = json.dumps(record, indent=2, sort_keys=False)
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
        cost = record["cost"]
        usd = cost["estimated_usd"]
        sys.stderr.write(
            "wrote {0}: {1} total tokens, {2}, {3}s wall clock, {4} tool calls\n".format(
                out_path,
                cost["total_tokens"],
                "${0:.4f}".format(usd) if usd is not None else "usd unknown (no rate on file)",
                record["time"]["agent_wall_clock_seconds"],
                cost["tool_calls"],
            )
        )
    else:
        sys.stdout.write(payload + "\n")

    if args.print_detection:
        stats = record["provenance"]["parse_stats"]
        sys.stderr.write(json.dumps({"parse_stats": stats}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Aggregate k run records per arm into an ascent.eval-suite-summary.v1 document.

    python3 -m evals.lib.aggregate --suite context-skills

Reads `evals/<suite-id>/results/runs/*.json` and writes
`evals/<suite-id>/results/latest.json`.

The spread matters more than the mean. Per the spec: "A cheap average with a wide
spread is a worse product than a slightly dearer run that lands in the same place
every time, because consistency is what we are selling."

Consistency verdict, from the coefficient of variation of `total_tokens` within
an arm. Thresholds are PROVISIONAL and recorded so they can be argued with:

    CV < 0.10        predictable      cost per run is safe to quote to a client
    0.10 <= CV <= 0.30  variable      budget with headroom; investigate the spread
    CV > 0.30        unpredictable    do not quote a per-run cost

One run gives no spread at all. A single sample yields `coefficient_of_variation:
null` and the verdict `insufficient-runs` - never a fake 0.0, which would read as
"perfectly predictable" off one data point. Two samples produce a CV, but the
verdict stays `insufficient-runs` below `MIN_RUNS_FOR_VERDICT` runs because a
two-point spread is not evidence.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SUITE_SUMMARY_SCHEMA = "ascent.eval-suite-summary.v1"
RUN_RECORD_SCHEMA = "ascent.eval-run-record.v1"

WITH_SKILLS = "with-skills"
BASELINE = "baseline-no-skills"
ARMS = (WITH_SKILLS, BASELINE)

CV_PREDICTABLE = 0.10
CV_UNPREDICTABLE = 0.30
MIN_RUNS_FOR_VERDICT = 3

VERDICT_PREDICTABLE = "predictable"
VERDICT_VARIABLE = "variable"
VERDICT_UNPREDICTABLE = "unpredictable"
VERDICT_INSUFFICIENT = "insufficient-runs"

REPO_ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- stats


def percentile(values: Sequence[float], fraction: float) -> Optional[float]:
    """Linear-interpolated percentile. `fraction` in [0, 1]. None for an empty series."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = fraction * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def coefficient_of_variation(values: Sequence[float]) -> Optional[float]:
    """Sample standard deviation over the mean. None when undefined.

    Undefined for fewer than two samples (no spread to measure) and for a zero
    mean (nothing to normalise against). Returns None in both cases rather than
    0.0 - "how much the cost jumps around" is unknown, not zero.
    """
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) / abs(mean)


def consistency_verdict(values: Sequence[float]) -> str:
    """Map a series of per-run totals to a provisional consistency verdict."""
    if len(values) < MIN_RUNS_FOR_VERDICT:
        return VERDICT_INSUFFICIENT
    cv = coefficient_of_variation(values)
    if cv is None:
        return VERDICT_INSUFFICIENT
    if cv < CV_PREDICTABLE:
        return VERDICT_PREDICTABLE
    if cv <= CV_UNPREDICTABLE:
        return VERDICT_VARIABLE
    return VERDICT_UNPREDICTABLE


def _spread(values: Sequence[float], keys: Sequence[str], as_int: bool = False) -> Dict[str, Any]:
    """Build a spread block containing exactly `keys`."""
    out: Dict[str, Any] = {}
    if not values:
        for key in keys:
            out[key] = None
        return out

    def shape(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        return int(round(value)) if as_int else round(value, 6)

    computed = {
        "min": shape(min(values)),
        "p50": shape(percentile(values, 0.50)),
        "p95": shape(percentile(values, 0.95)),
        "max": shape(max(values)),
        "mean": shape(sum(values) / len(values)),
    }
    for key in keys:
        if key == "coefficient_of_variation":
            cv = coefficient_of_variation(values)
            out[key] = None if cv is None else round(cv, 4)
        else:
            out[key] = computed.get(key)
    return out


# ------------------------------------------------------------------- run discovery


def suite_dir(suite_id: str, root: Optional[Path] = None) -> Path:
    base = root if root is not None else REPO_ROOT
    return base / "evals" / suite_id


def runs_dir(suite_id: str, root: Optional[Path] = None) -> Path:
    return suite_dir(suite_id, root) / "results" / "runs"


def load_runs(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    """Load run records, skipping files that are not run records at all."""
    records: List[Dict[str, Any]] = []
    for path in sorted(paths):
        try:
            with path.open("r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError) as exc:
            sys.stderr.write("warning: skipping {0}: {1}\n".format(path, exc))
            continue
        if not isinstance(record, dict):
            sys.stderr.write("warning: skipping {0}: not a JSON object\n".format(path))
            continue
        if record.get("schema_version") != RUN_RECORD_SCHEMA:
            sys.stderr.write(
                "warning: skipping {0}: schema_version is {1!r}, expected {2!r}\n".format(
                    path, record.get("schema_version"), RUN_RECORD_SCHEMA
                )
            )
            continue
        record["_source_path"] = str(path)
        records.append(record)
    return records


def discover_runs(suite_id: str, root: Optional[Path] = None) -> List[Dict[str, Any]]:
    directory = runs_dir(suite_id, root)
    if not directory.is_dir():
        return []
    return load_runs(list(directory.glob("*.json")))


# ---------------------------------------------------------------------- aggregation


def _numbers(records: Sequence[Dict[str, Any]], block: str, field: str) -> List[float]:
    out: List[float] = []
    for record in records:
        section = record.get(block)
        if not isinstance(section, dict):
            continue
        value = section.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        out.append(float(value))
    return out


def _pass_rate(records: Sequence[Dict[str, Any]]) -> Optional[float]:
    outcomes = []
    for record in records:
        correctness = record.get("correctness")
        if not isinstance(correctness, dict):
            continue
        outcome = correctness.get("outcome")
        if isinstance(outcome, str):
            outcomes.append(1.0 if outcome == "pass" else 0.0)
    if not outcomes:
        return None
    return round(sum(outcomes) / len(outcomes), 4)


def _consistent_baseline(records: Sequence[Dict[str, Any]]):
    """Return (minutes, source) when every run recording a baseline agrees.

    Disagreement returns (None, None): a human baseline is a recorded fact, and
    two different recorded facts for the same deliverable is a data problem to
    surface, not something to average.
    """
    values = set()
    sources = set()
    for record in records:
        time_block = record.get("time")
        if not isinstance(time_block, dict):
            continue
        minutes = time_block.get("human_baseline_minutes")
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)):
            continue
        values.add(float(minutes))
        source = time_block.get("human_baseline_source")
        if isinstance(source, str) and source:
            sources.add(source)
    if len(values) != 1:
        return None, None
    return values.pop(), (sources.pop() if len(sources) == 1 else None)


def _credit_totals(records: Sequence[Dict[str, Any]]) -> List[float]:
    """Per-run derived credit totals, skipping runs with no priced turn."""
    out: List[float] = []
    for record in records:
        cost = record.get("cost")
        if not isinstance(cost, dict):
            continue
        credits = cost.get("credits")
        if not isinstance(credits, dict):
            continue
        value = credits.get("total")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        out.append(float(value))
    return out


def _reconciliation_total(records: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Sum the token reconciliation invariant across an arm's runs.

    Surfaced rather than hidden: a run whose per-request deltas do not reconcile
    is a run whose in-run spread is partly unexplained, and a reader deciding
    whether to quote a price needs to know how often that happened.
    """
    checked = holds = violates = 0
    seen = False
    for record in records:
        cost = record.get("cost")
        if not isinstance(cost, dict):
            continue
        credits = cost.get("credits")
        if not isinstance(credits, dict):
            continue
        block = credits.get("reconciliation_invariant")
        if not isinstance(block, dict):
            continue
        seen = True
        checked += int(block.get("checked") or 0)
        holds += int(block.get("holds") or 0)
        violates += int(block.get("violates") or 0)
    if not seen:
        return None
    return {
        "checked": checked,
        "holds": holds,
        "violates": violates,
        "rate": round(holds / checked, 6) if checked else None,
    }


def _skill_call_seconds(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-skill call counts and durations, summed across an arm's runs."""
    out: Dict[str, Any] = {}
    for record in records:
        time_block = record.get("time")
        if not isinstance(time_block, dict):
            continue
        by_skill = time_block.get("skill_call_seconds_by_skill")
        if not isinstance(by_skill, dict):
            continue
        for skill, entry in by_skill.items():
            if not isinstance(entry, dict):
                continue
            bucket = out.setdefault(
                str(skill), {"runs_invoking": 0, "calls": 0, "total_seconds": 0.0, "reading": None}
            )
            bucket["runs_invoking"] += 1
            bucket["calls"] += int(entry.get("calls") or 0)
            seconds = entry.get("total_seconds")
            if isinstance(seconds, (int, float)) and not isinstance(seconds, bool):
                bucket["total_seconds"] = round(bucket["total_seconds"] + float(seconds), 3)
            if entry.get("reading") and not bucket["reading"]:
                bucket["reading"] = entry["reading"]
    for bucket in out.values():
        if bucket["reading"] is None:
            bucket.pop("reading")
    return out


def summarise_arm(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Build one arm block of the suite summary."""
    tokens = _numbers(records, "cost", "total_tokens")
    usd = _numbers(records, "cost", "estimated_usd")
    wall = _numbers(records, "time", "agent_wall_clock_seconds")
    credits = _credit_totals(records)
    utilisation = _numbers(records, "cost", "peak_context_utilization")
    requests = _numbers(records, "cost", "model_requests")

    arm: Dict[str, Any] = {
        "runs": len(records),
        "correctness_pass_rate": _pass_rate(records),
        "total_tokens": _spread(
            tokens, ("min", "p50", "p95", "max", "mean", "coefficient_of_variation"), as_int=True
        ),
        "estimated_usd": _spread(usd, ("min", "p50", "max")),
        "credits": _spread(
            credits, ("min", "p50", "p95", "max", "mean", "coefficient_of_variation")
        ),
        "wall_clock_seconds": _spread(
            wall, ("min", "p50", "max", "coefficient_of_variation"), as_int=False
        ),
        "model_requests": _spread(requests, ("min", "p50", "max", "mean"), as_int=True),
        "peak_context_utilization": _spread(utilisation, ("min", "p50", "max")),
        "consistency_verdict": consistency_verdict(tokens),
        "skill_call_seconds": _skill_call_seconds(records),
    }

    if credits:
        # The consistency verdict is defined over tokens by the spec. Credits are
        # the unit a Codex user is actually billed in, so its own verdict is
        # reported beside it rather than folded into the token one.
        arm["credits_consistency_verdict"] = consistency_verdict(credits)
        arm["credits_derivation"] = (
            "derived: measured token deltas x the published rate card in "
            "evals/lib/telemetry/codex_rates.json"
        )
    else:
        arm["credits_unavailable_reason"] = (
            "No run in this arm recorded a derived credit total. Credits apply to "
            "Codex sessions whose turn model is on the published rate card; a Claude "
            "Code run is billed in dollars and reports estimated_usd instead."
        )
    if credits and len(credits) < len(records):
        arm["credits_note"] = (
            "{0} of {1} runs produced no credit figure and are excluded rather than "
            "counted as zero".format(len(records) - len(credits), len(records))
        )

    reconciliation = _reconciliation_total(records)
    if reconciliation is not None:
        arm["token_reconciliation"] = reconciliation

    if len(usd) < len(records):
        arm["estimated_usd_note"] = (
            "{0} of {1} runs have no recorded rate for their model; "
            "dollar spread covers only the priced runs".format(len(records) - len(usd), len(records))
        )

    minutes, source = _consistent_baseline(records)
    if minutes is not None:
        arm["human_baseline_minutes"] = minutes
        if source:
            arm["human_baseline_source"] = source
        p50_wall = percentile(wall, 0.50)
        if p50_wall is not None:
            arm["time_saved_minutes_p50"] = round(minutes - p50_wall / 60.0, 2)

    return arm


def _delta(new: Optional[float], old: Optional[float]) -> Optional[float]:
    if new is None or old is None:
        return None
    return old - new


def compute_deltas(arms: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Difference between the with-skills and baseline arms.

    Returns None when the baseline arm has no runs. Per the spec, every headline
    claim is a delta, never an absolute - so with no baseline there is no
    reportable saving, and emitting zeros would invent one.
    """
    treated = arms.get(WITH_SKILLS)
    control = arms.get(BASELINE)
    if not treated or not control or not control.get("runs") or not treated.get("runs"):
        return None

    tokens_saved = _delta(treated["total_tokens"]["p50"], control["total_tokens"]["p50"])
    usd_saved = _delta(treated["estimated_usd"]["p50"], control["estimated_usd"]["p50"])
    wall_saved = _delta(treated["wall_clock_seconds"]["p50"], control["wall_clock_seconds"]["p50"])
    credits_saved = _delta(
        (treated.get("credits") or {}).get("p50"), (control.get("credits") or {}).get("p50")
    )

    deltas: Dict[str, Any] = {
        "tokens_saved_p50": None if tokens_saved is None else int(round(tokens_saved)),
        "usd_saved_p50": None if usd_saved is None else round(usd_saved, 6),
        "credits_saved_p50": None if credits_saved is None else round(credits_saved, 6),
        "minutes_saved_p50": None if wall_saved is None else round(wall_saved / 60.0, 2),
        "correctness_pass_rate_delta": _pass_rate_delta(treated, control),
        "consistency_improvement": _consistency_improvement(treated, control),
    }
    return deltas


def _pass_rate_delta(treated: Dict[str, Any], control: Dict[str, Any]) -> Optional[float]:
    a = treated.get("correctness_pass_rate")
    b = control.get("correctness_pass_rate")
    if a is None or b is None:
        return None
    return round(a - b, 4)


def _consistency_improvement(treated: Dict[str, Any], control: Dict[str, Any]) -> str:
    a = treated["total_tokens"].get("coefficient_of_variation")
    b = control["total_tokens"].get("coefficient_of_variation")
    if a is None or b is None:
        return (
            "unknown: fewer than two runs in at least one arm, so how much the cost "
            "jumps around cannot be compared"
        )
    return "with-skills cost variation {0:.4f} vs baseline {1:.4f} ({2} vs {3})".format(
        a, b, treated["consistency_verdict"], control["consistency_verdict"]
    )


def build_summary(
    suite_id: str,
    records: Sequence[Dict[str, Any]],
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an `ascent.eval-suite-summary.v1` document from run records."""
    by_arm: Dict[str, List[Dict[str, Any]]] = {arm: [] for arm in ARMS}
    unknown_arms: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        arm = record.get("arm")
        if arm in by_arm:
            by_arm[arm].append(record)
        else:
            unknown_arms.setdefault(str(arm), []).append(record)

    arms = {arm: summarise_arm(by_arm[arm]) for arm in ARMS}
    for arm, extra in unknown_arms.items():
        arms[arm] = summarise_arm(extra)

    counts = [arms[arm]["runs"] for arm in arms if arms[arm]["runs"]]
    runs_per_arm = min(counts) if counts else 0

    stamp = generated_at or (
        _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

    summary: Dict[str, Any] = {
        "schema_version": SUITE_SUMMARY_SCHEMA,
        "suite_id": suite_id,
        "generated_at": stamp,
        "runs_per_arm": runs_per_arm,
        "arms": arms,
        "deltas": compute_deltas(arms),
    }

    summary["consistency_thresholds"] = {
        "metric": "coefficient_of_variation(total_tokens)",
        "predictable": "< {0}".format(CV_PREDICTABLE),
        "variable": "{0}-{1}".format(CV_PREDICTABLE, CV_UNPREDICTABLE),
        "unpredictable": "> {0}".format(CV_UNPREDICTABLE),
        "minimum_runs_for_verdict": MIN_RUNS_FOR_VERDICT,
        "status": "provisional",
    }

    notes: List[str] = []
    if runs_per_arm and any(arms[arm]["runs"] != runs_per_arm for arm in arms if arms[arm]["runs"]):
        notes.append(
            "arms have unequal run counts; runs_per_arm is the minimum and each arm "
            "carries its own runs field"
        )
    if summary["deltas"] is None:
        notes.append(
            "deltas is null: the baseline-no-skills arm has no runs, so nothing here "
            "is a measured saving"
        )
    if unknown_arms:
        notes.append(
            "run records carried arms outside the spec's two: {0}".format(
                ", ".join(sorted(unknown_arms))
            )
        )
    if notes:
        summary["notes"] = notes

    return summary


# ------------------------------------------------------------------------------ CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m evals.lib.aggregate",
        description="Aggregate run records into an ascent.eval-suite-summary.v1 document.",
    )
    parser.add_argument("--suite", required=True, help="suite id, e.g. context-skills")
    parser.add_argument(
        "--runs-dir",
        help="override the run-record directory (default: evals/<suite>/results/runs)",
    )
    parser.add_argument(
        "--out",
        help="output path (default: evals/<suite>/results/latest.json; '-' for stdout)",
    )
    parser.add_argument(
        "--root",
        help="repository root, for use outside a checkout",
    )
    parser.add_argument(
        "--print",
        dest="print_summary",
        action="store_true",
        help="also print the summary to stdout when writing to a file",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser() if args.root else None

    if args.runs_dir:
        directory = Path(args.runs_dir).expanduser()
        if not directory.is_dir():
            sys.stderr.write("error: no such runs directory: {0}\n".format(directory))
            return 2
        records = load_runs(list(directory.glob("*.json")))
    else:
        directory = runs_dir(args.suite, root)
        if not directory.is_dir():
            sys.stderr.write(
                "error: no run records for suite {0!r}: {1} does not exist\n".format(
                    args.suite, directory
                )
            )
            return 2
        records = discover_runs(args.suite, root)

    if not records:
        sys.stderr.write("error: no valid run records found in {0}\n".format(directory))
        return 2

    summary = build_summary(args.suite, records)
    payload = json.dumps(summary, indent=2, sort_keys=False)

    if args.out == "-":
        sys.stdout.write(payload + "\n")
        return 0

    out_path = (
        Path(args.out).expanduser()
        if args.out
        else suite_dir(args.suite, root) / "results" / "latest.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload + "\n", encoding="utf-8")
    sys.stderr.write(
        "wrote {0}: {1} runs across {2} arms\n".format(
            out_path, len(records), sum(1 for arm in summary["arms"].values() if arm["runs"])
        )
    )
    if args.print_summary:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

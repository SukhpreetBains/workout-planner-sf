"""Codex credit derivation. The rate card lives in `codex_rates.json`, never here.

Credits are a **derived** figure: measured tokens multiplied by a published rate.
Nothing in this module measures anything and nothing in it knows a rate. Every
number it returns can be traced back to a `last_token_usage` delta parsed out of
a rollout file and a rate read out of `codex_rates.json`, whose `source` block
carries the URL and the fetch date.

Three rules are load-bearing, all recorded in the rate card's own
`token_semantics` block, and all of them silently produce a wrong number if
missed:

1. **Codex token semantics are inverted from Claude Code's.**
   `cached_input_tokens` is a SUBSET of `input_tokens`, so billable uncached
   input is `input_tokens - cached_input_tokens`. Adding them together
   double-charges every cache read.
2. **`reasoning_output_tokens` is a SUBSET of `output_tokens`.** It is carried
   through to the run record because a reader wants to see it, and it is never
   added to anything. `credits_for_usage` does not even accept it.
3. **The billing unit is a TURN, not a model request.** The published
   "5-30 credits per message" band is per user turn. One turn drives many
   requests, so per-request statistics are not comparable to the published band.
   Grouping is the caller's job; `spread` is unit-agnostic and the caller labels
   the unit it passed.

Unpriced models return None, never 0.0. `gpt-5.5` is genuinely off the current
card; `codex-auto-review` is a router alias whose effective model has to be
resolved from `turn_context` before a rate can apply. A zero in a client-facing
cost figure is a false claim; a null is a missing one.

Reproduction check, run against the 26 local rollouts on 2026-08-25: grouping by
`turn_context.turn_id` and restricting to turns whose model is on the rate card
reproduces the card's own `measured_2026_08_25` block exactly - 58 priced turns,
mean 14.08 credits per turn, and per-model medians of 2.54 (terra, n=41), 0.65
(luna, n=9) and maxima of 29.69 / 2.83 / 338.29. The card's percentile figures
were taken with a different interpolation method, so p95 here reads lower; the
medians, means, counts and maxima agree to the stated precision.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

RATES_PATH = Path(__file__).resolve().parent / "codex_rates.json"

CREDIT_UNIT_DIVISOR = 1_000_000.0  # the card's unit: "credits per 1000000 tokens"

BILLING_UNIT_TURN = "turn"

_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}


def load_rates(path=None, reload: bool = False) -> Dict[str, Any]:
    """Load and memoise the frozen rate card."""
    target = Path(path) if path is not None else RATES_PATH
    key = str(target)
    with _LOCK:
        if reload or key not in _CACHE:
            with target.open("r", encoding="utf-8") as handle:
                _CACHE[key] = json.load(handle)
        return _CACHE[key]


def rate_for(model: Optional[str], rates: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, float]]:
    """Return the credits-per-million table for `model`, or None when unpriced."""
    if not model:
        return None
    data = rates if rates is not None else load_rates()
    entry = (data.get("rates") or {}).get(model)
    if not isinstance(entry, dict):
        return None
    return dict(entry)


def unpriced_reason(model: Optional[str], rates: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """The card's own recorded explanation for a model it does not price."""
    if not model:
        return None
    data = rates if rates is not None else load_rates()
    reason = (data.get("unpriced") or {}).get(model)
    return reason if isinstance(reason, str) else None


def is_router_alias(model: Optional[str], rates: Optional[Dict[str, Any]] = None) -> bool:
    """True when the card records this name as an alias rather than a billable model."""
    reason = unpriced_reason(model, rates)
    return bool(reason) and "alias" in reason.lower()


def priced_models(rates: Optional[Dict[str, Any]] = None) -> List[str]:
    data = rates if rates is not None else load_rates()
    return sorted((data.get("rates") or {}).keys())


def credits_for_usage(
    model: Optional[str],
    input_tokens: int = 0,
    cached_input_tokens: int = 0,
    output_tokens: int = 0,
    rates: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    """Credits for one usage delta, or None when the model has no published rate.

    `input_tokens` is Codex's reported figure, which *contains*
    `cached_input_tokens`; the cached portion is billed at the cached rate and
    only the remainder at the uncached rate. There is deliberately no
    `reasoning_output_tokens` parameter: reasoning is already inside
    `output_tokens` and adding it would double-count.
    """
    rate = rate_for(model, rates)
    if rate is None:
        return None
    cached = max(int(cached_input_tokens or 0), 0)
    total_input = max(int(input_tokens or 0), 0)
    uncached = max(total_input - cached, 0)
    output = max(int(output_tokens or 0), 0)
    value = (
        uncached * float(rate["input"])
        + cached * float(rate["cached_input"])
        + output * float(rate["output"])
    ) / CREDIT_UNIT_DIVISOR
    return round(value, 6)


# ---------------------------------------------------------------- provenance


def source_block(rates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The rate card's citation, so a displayed credit figure can name its source."""
    data = rates if rates is not None else load_rates()
    source = dict(data.get("source") or {})
    source["schema"] = data.get("schema")
    source["unit"] = data.get("unit")
    source["rate_card_file"] = RATES_PATH.name
    return source


def unquantified_multipliers(rates: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Published multipliers with no numeric factor on file.

    Both of these make a derived credit figure an *understatement* rather than an
    estimate, so they travel with the number rather than in a footnote nobody
    reads.
    """
    data = rates if rates is not None else load_rates()
    entries = data.get("unquantified_multipliers")
    return [dict(item) for item in entries if isinstance(item, dict)] if isinstance(entries, list) else []


def billing_unit_note(rates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = rates if rates is not None else load_rates()
    return dict(data.get("billing_unit_warning") or {})


def reconciliation_rule(rates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = rates if rates is not None else load_rates()
    return dict(data.get("reconciliation_invariant") or {})


def token_semantics(rates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = rates if rates is not None else load_rates()
    return dict(data.get("token_semantics") or {})


# ---------------------------------------------------------------------- stats


def percentile(values: Sequence[float], fraction: float) -> Optional[float]:
    """Linear-interpolated percentile. None for an empty series."""
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def spread(values: Sequence[float], unit: str) -> Optional[Dict[str, Any]]:
    """Distribution of a credit series, tagged with the unit it was measured in.

    `unit` is not decoration. A median of 0.84 credits per *request* and a median
    of 2.59 credits per *turn* describe the same corpus, and only the second is
    comparable to the published per-message band. An untagged number invites the
    wrong comparison.
    """
    series = [float(v) for v in values]
    if not series:
        return None
    mean = sum(series) / len(series)
    block: Dict[str, Any] = {
        "unit": unit,
        "n": len(series),
        "min": round(min(series), 6),
        "p50": round(percentile(series, 0.50), 6),
        "p95": round(percentile(series, 0.95), 6),
        "max": round(max(series), 6),
        "mean": round(mean, 6),
        "total": round(sum(series), 6),
    }
    if len(series) >= 2 and mean != 0:
        variance = sum((value - mean) ** 2 for value in series) / (len(series) - 1)
        block["coefficient_of_variation"] = round(variance ** 0.5 / abs(mean), 6)
    else:
        block["coefficient_of_variation"] = None
        block["coefficient_of_variation_unavailable_reason"] = (
            "A spread needs at least two priced turns with a non-zero mean."
        )
    return block

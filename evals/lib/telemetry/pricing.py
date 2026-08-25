"""Per-model rate loader. Never hardcode a price in code - it lives in pricing.json.

Rates were retrieved by invoking the `claude-api` skill rather than recalled, and
each model entry carries the `checked_on` date the spec asks for. Cache reads and
cache writes are priced separately from uncached input.

A model with no recorded rate returns None from `price_usage` rather than 0.0 - a
false zero in a cost report is worse than a visible gap.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional

PRICING_PATH = Path(__file__).resolve().parent / "pricing.json"

_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}


class UnknownModelRate(LookupError):
    """Raised only by `require_rate`; `rate_for` returns None instead."""


def load_pricing(path=None, reload: bool = False) -> Dict[str, Any]:
    """Load and memoise pricing.json."""
    target = Path(path) if path is not None else PRICING_PATH
    key = str(target)
    with _LOCK:
        if reload or key not in _CACHE:
            with target.open("r", encoding="utf-8") as handle:
                _CACHE[key] = json.load(handle)
        return _CACHE[key]


def normalise_model(model: Optional[str], pricing: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Resolve aliases and context-window suffixes to a canonical model key.

    Handles the `[1m]` long-context suffix and the Bedrock `anthropic.` prefix,
    both of which name the same rate card as the bare model id.
    """
    if not model:
        return None
    data = pricing if pricing is not None else load_pricing()
    models = data.get("models", {})
    aliases = data.get("aliases", {})
    name = model.strip()
    if name in models:
        return name
    if name in aliases:
        return aliases[name]
    seen = set()
    while name in aliases and name not in seen:
        seen.add(name)
        name = aliases[name]
    if name in models:
        return name
    if name.endswith("]") and "[" in name:
        stripped = name[: name.rindex("[")]
        if stripped in models:
            return stripped
        if stripped in aliases:
            return aliases[stripped]
    if name.startswith("anthropic."):
        stripped = name[len("anthropic.") :]
        if stripped in models:
            return stripped
    return None


def rate_for(model: Optional[str], pricing: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, float]]:
    """Return the USD-per-million rate table for `model`, or None if unrecorded."""
    data = pricing if pricing is not None else load_pricing()
    key = normalise_model(model, data)
    if key is None:
        return None
    entry = data["models"][key]
    return dict(entry["usd_per_million"])


def require_rate(model: Optional[str], pricing: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """Like `rate_for`, but raise rather than return None. For callers that must price."""
    rate = rate_for(model, pricing)
    if rate is None:
        raise UnknownModelRate(
            "no recorded rate for model {0!r}; add it to {1} with a checked_on date".format(
                model, PRICING_PATH
            )
        )
    return rate


def checked_on(model: Optional[str], pricing: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Return the date the rate for `model` was last verified."""
    data = pricing if pricing is not None else load_pricing()
    key = normalise_model(model, data)
    if key is None:
        return None
    return data["models"][key].get("checked_on")


def price_usage(
    model: Optional[str],
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_write_ttl: Optional[str] = None,
    pricing: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    """Price one usage tuple in USD, or None when the model has no recorded rate.

    Cache reads and cache writes are billed at their own rates, so a cache-heavy
    session is not charged as if every token were fresh input.
    """
    data = pricing if pricing is not None else load_pricing()
    rate = rate_for(model, data)
    if rate is None:
        return None
    ttl = cache_write_ttl or data.get("cache_write_default_ttl", "5m")
    write_key = "cache_write_{0}".format(ttl)
    write_rate = rate.get(write_key)
    if write_rate is None:
        write_rate = rate.get("cache_write_5m", rate["input"])
    total = (
        input_tokens * rate["input"]
        + output_tokens * rate["output"]
        + cache_read_tokens * rate["cache_read"]
        + cache_creation_tokens * write_rate
    ) / 1_000_000.0
    return round(total, 6)


def is_unpriced(model: Optional[str], pricing: Optional[Dict[str, Any]] = None) -> bool:
    """True when the model is explicitly recorded as having no rate on file."""
    if not model:
        return False
    data = pricing if pricing is not None else load_pricing()
    return model in data.get("unpriced_models", {})

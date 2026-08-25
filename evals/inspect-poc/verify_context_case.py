#!/usr/bin/env python3
"""Outcome verifier used exclusively by the sandboxed Inspect POC."""

from __future__ import annotations

import json
from pathlib import Path


SENTINEL = "RESTRICTED_EMAIL_BODY_MUST_NOT_LEAK"
REQUIRED = {"mobilize-gate", "validated-scope", "governance-model"}


def main() -> None:
    samples = json.loads(Path("cases.json").read_text(encoding="utf-8"))
    sample = samples[0]
    metadata = sample["metadata"]
    if set(metadata["required_chunk_ids"]) != REQUIRED:
        raise SystemExit("fixture does not include every required evidence outcome")
    if metadata["forbidden_text"] != SENTINEL:
        raise SystemExit("fixture does not protect the restricted-body sentinel")
    if SENTINEL in sample["input"] + sample["target"]:
        raise SystemExit("fixture leaked restricted source content")
    print("CONTEXT_EVAL_PASS")


if __name__ == "__main__":
    main()

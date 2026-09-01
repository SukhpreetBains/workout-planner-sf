#!/usr/bin/env python3
"""Grade the reference-informed source-content to editable-PPTX path."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[1]
SKILL_DIR = ROOT / "skills" / "compose-deliverable"
SOURCE_CONTRACT = EVAL_DIR / "cases" / "reference-informed-source.json"
BUILD = SKILL_DIR / "scripts" / "build.mjs"
VALIDATOR = SKILL_DIR / "scripts" / "validate_pptx.py"
NEGATIVE_CASES = SKILL_DIR / "scripts" / "test" / "validator_cases.py"


def command(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)


def require(result: subprocess.CompletedProcess[str], check_id: str) -> None:
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "command failed without output"
        raise RuntimeError(f"{check_id}: {message}")


def run_once() -> dict:
    contract = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    passed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ascent-compose-deliverable-eval-") as temporary:
        temporary_dir = Path(temporary)
        deck = temporary_dir / "reference-informed.pptx"
        manifest = deck.with_suffix(".manifest.json")
        build = command(["node", str(BUILD), str(ROOT / contract["fixture"]), "--storyboard", str(ROOT / contract["storyboard"]), "--out", str(deck)], SKILL_DIR)
        require(build, "build-reference-informed-deck")
        if not deck.is_file() or not manifest.is_file():
            raise RuntimeError("build-artifacts-exist: build did not write both deck and manifest")
        passed.extend(["build-reference-informed-deck", "build-artifacts-exist"])

        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        if len(manifest_data.get("slides", [])) != contract["expected_slide_count"]:
            raise RuntimeError("storyboard-slide-count: generated manifest does not match the declared slide count")
        if len(manifest_data.get("sections", [])) != contract["expected_section_count"]:
            raise RuntimeError("source-section-count: generated manifest does not match the declared source section count")
        if any(not section.get("slideNumbers") for section in manifest_data["sections"]):
            raise RuntimeError("source-section-coverage: at least one source section has no deck slide")
        passed.extend(["storyboard-slide-count", "source-section-count", "source-section-coverage"])

        validation_args = [sys.executable, str(VALIDATOR), str(deck), "--manifest", str(manifest)]
        for text in contract["required_native_text"]:
            validation_args.extend(["--expect-text", text])
        require(command(validation_args, SKILL_DIR), "source-content-survives-as-native-text")
        passed.append("source-content-survives-as-native-text")

        require(command([sys.executable, str(NEGATIVE_CASES), str(deck), str(manifest)], SKILL_DIR), "corrupted-decks-are-rejected")
        passed.append("corrupted-decks-are-rejected")
    return {"checks_total": 7, "checks_passed": len(passed), "check_ids": passed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=1, help="Whole-suite repeats for the eval workbench.")
    parser.add_argument("--quiet", action="store_true", help="Only emit the final JSON result.")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    completed, failed, check_ids = 0, [], []
    for attempt in range(1, args.runs + 1):
        try:
            result = run_once()
            completed += 1
            check_ids = result["check_ids"]
            if not args.quiet:
                print(f"PASS: run {attempt}/{args.runs} ({result['checks_passed']} checks)")
        except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as error:
            failed.append(f"run-{attempt}: {error}")
            if not args.quiet:
                print(f"FAIL: run {attempt}/{args.runs}: {error}", file=sys.stderr)

    passed = not failed and completed == args.runs
    payload = {"suite": "compose-deliverable", "arm": "with-skills", "outcome": "pass" if passed else "fail", "checks_total": 7 * args.runs, "checks_passed_min": 7 * completed if passed else 7 * max(completed - 1, 0), "evaluated_task_count": 2, "outcome_pass_rate": completed / args.runs, "failed_check_ids": failed, "check_ids": check_ids}
    print(json.dumps(payload, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

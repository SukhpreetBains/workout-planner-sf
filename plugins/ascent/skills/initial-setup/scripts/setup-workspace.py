#!/usr/bin/env python3
"""Initialize trackers, identity, derived state, and report readiness."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_SCRIPTS = SCRIPT_DIR.parents[2] / "shared" / "scripts"


def run_step(label: str, script: Path, args: list[str], env: dict[str, str]) -> None:
    print(f"\n{label}", flush=True)
    result = subprocess.run([sys.executable, str(script), *args], env=env, check=False)
    if result.returncode:
        raise RuntimeError(f"{script.name} failed with exit code {result.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity", required=True, help="Opportunity folder path.")
    parser.add_argument("--account", required=True, help="Confirmed Account name.")
    parser.add_argument("--opportunity-name", required=True, help="Confirmed Opportunity name.")
    args = parser.parse_args()

    root = Path(args.opportunity).expanduser().resolve()
    if not root.is_dir():
        print(f"Opportunity folder does not exist: {root}", file=sys.stderr)
        return 2
    if not (root / "workspace").is_dir():
        print(f"Workspace folder does not exist: {root / 'workspace'}", file=sys.stderr)
        return 2
    if not args.account.strip() or not args.opportunity_name.strip():
        print("Account and Opportunity names cannot be blank.", file=sys.stderr)
        return 2

    env = {**os.environ, "ASCENT_OPPORTUNITY_ROOT": str(root)}
    try:
        run_step("[1/4] Initialize trackers", SHARED_SCRIPTS / "init_trackers.py", [], env)
        run_step(
            "[2/4] Record project identity",
            SCRIPT_DIR / "record-identity.py",
            ["--opportunity", str(root), "--account", args.account,
             "--opportunity-name", args.opportunity_name],
            env,
        )
        run_step("[3/4] Build search index", SHARED_SCRIPTS / "sync.py", [], env)
        run_step("[4/4] Setup readiness", SHARED_SCRIPTS / "sync.py", ["--check-setup"], env)
    except RuntimeError as error:
        print(f"\nSetup stopped: {error}", file=sys.stderr)
        return 1

    print("\nSetup workspace readiness: READY")
    print(f"Opportunity: {root}")
    print("Trackers, identity, tracker copies, search index, and sync state are ready.")
    print("\nAfter the final setup checklist, add your first source document:")
    print(f"Place it in: {root / 'workspace' / 'inbox'}")
    print("If it is already there, leave it in place.")
    print(
        "Then start a fresh conversation with this Opportunity folder open, "
        "so setup history does not fill the ingestion context."
    )
    print("Use workspace-add to process the documents in this Opportunity workspace inbox.")
    print(
        "If ingestion proposes updates, review them in the review inbox "
        "before they enter the trackers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

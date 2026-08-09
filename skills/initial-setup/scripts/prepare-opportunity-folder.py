#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


INVALID_NAME_CHARACTERS = set('"*/:<>?\\|#%')
TEMPLATE_PATHS = (
    ("Content Inbox",),
    ("Content Inbox", "Transcripts"),
    ("Content Inbox", "Email Threads"),
    ("Content Inbox", "Client Docs"),
    ("Agent Inbox",),
    ("Agent Inbox", "In Progress"),
    ("Agent Inbox", "Ready for Review"),
    ("Deliverables",),
    ("Deliverables", "Mobilize"),
    ("Deliverables", "Discover"),
    ("Deliverables", "Deliver"),
    ("Deliverables", "Transition"),
)
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def validate_opportunity_name(name: str) -> str:
    candidate = name.strip()
    if not candidate:
        raise ValueError("Project name cannot be empty.")
    if candidate != name or candidate.endswith("."):
        raise ValueError("Project name cannot start or end with spaces or end with a period.")
    if candidate in {".", ".."}:
        raise ValueError("Project name cannot be '.' or '..'.")
    if len(candidate) > 128:
        raise ValueError("Project name must be 128 characters or fewer.")
    if any(character in INVALID_NAME_CHARACTERS or ord(character) < 32 for character in candidate):
        raise ValueError(
            "Project name contains characters that are unsafe for SharePoint, OneDrive, or Windows."
        )

    base_name = candidate.split(".", 1)[0].upper()
    if base_name in WINDOWS_RESERVED_NAMES:
        raise ValueError("Project name uses a reserved Windows device name.")
    return candidate


def print_template_status(opportunity_path: Path) -> list[str]:
    missing: list[str] = []
    for path_parts in TEMPLATE_PATHS:
        folder_path = opportunity_path.joinpath(*path_parts)
        folder_name = "/".join(path_parts)
        if folder_path.is_dir():
            print(f"ready: {folder_path}")
        else:
            print(f"missing: {folder_path}")
            missing.append(folder_name)
    return missing


def check_local_write_readiness(path: Path) -> bool:
    if os.access(path, os.W_OK | os.X_OK):
        print(f"local write readiness: available ({path})")
        return True

    print(
        f"Local write readiness is unavailable for: {path}. "
        "Open the synced folder as the Codex workspace or grant local write access.",
        file=sys.stderr,
    )
    return False


def prepare_new_opportunity(opportunity_path: Path) -> int:
    if opportunity_path.exists():
        if opportunity_path.is_dir():
            print(
                f"Opportunity folder already exists: {opportunity_path}. "
                "Use --mode existing to inspect it.",
                file=sys.stderr,
            )
        else:
            print(
                f"Cannot create Opportunity folder because a file already exists: {opportunity_path}",
                file=sys.stderr,
            )
        return 1

    try:
        opportunity_path.mkdir()
        for path_parts in TEMPLATE_PATHS:
            opportunity_path.joinpath(*path_parts).mkdir()
    except OSError as error:
        print(f"Could not prepare Opportunity folder: {error}", file=sys.stderr)
        return 1

    print(f"created: {opportunity_path}")
    print_template_status(opportunity_path)
    print("OneDrive will sync this project structure to SharePoint when synchronization is healthy.")
    return 0


def inspect_existing_opportunity(opportunity_path: Path) -> int:
    if not opportunity_path.is_dir():
        print(
            f"Existing Opportunity folder was not found: {opportunity_path}",
            file=sys.stderr,
        )
        return 1

    print(f"using existing: {opportunity_path}")
    missing = print_template_status(opportunity_path)
    if missing:
        print(
            "No folders were created. Resolve missing folders in the source system or wait for OneDrive sync.",
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a new Opportunity folder or inspect an existing one."
    )
    parser.add_argument(
        "--mode",
        choices=("new", "existing"),
        required=True,
        help="Use 'new' to create a project template or 'existing' to inspect without changes.",
    )
    parser.add_argument(
        "--account-root",
        required=True,
        help="Local path to the existing OneDrive-synced Account folder.",
    )
    parser.add_argument(
        "--opportunity-name",
        required=True,
        help="Project name or existing Opportunity-folder name.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check the selected local path without creating or changing folders.",
    )
    args = parser.parse_args()

    try:
        opportunity_name = validate_opportunity_name(args.opportunity_name)
    except ValueError as error:
        print(f"Invalid project name: {error}", file=sys.stderr)
        return 2

    account_root = Path(args.account_root).expanduser().resolve()
    if not account_root.is_dir():
        print(
            f"Account folder does not exist or is not a directory: {account_root}",
            file=sys.stderr,
        )
        return 2

    opportunity_path = account_root / opportunity_name
    readiness_path = account_root if args.mode == "new" else opportunity_path
    if args.check_only:
        if args.mode == "existing" and not opportunity_path.is_dir():
            return inspect_existing_opportunity(opportunity_path)
        if not check_local_write_readiness(readiness_path):
            return 1
        print("check complete: no folders were created or changed")
        return 0

    if args.mode == "new":
        if not check_local_write_readiness(account_root):
            return 1
        return prepare_new_opportunity(opportunity_path)

    if not opportunity_path.is_dir():
        return inspect_existing_opportunity(opportunity_path)
    if not check_local_write_readiness(opportunity_path):
        return 1
    return inspect_existing_opportunity(opportunity_path)


if __name__ == "__main__":
    raise SystemExit(main())

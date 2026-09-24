#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


INVALID_NAME_CHARACTERS = set('"*/:<>?\\|#%')
DELIVERABLE_PATHS = (
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
AGENTS_FILE_NAME = "AGENTS.md"
SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKSPACE_TEMPLATE = SKILL_ROOT / "assets" / "workspace-template"
AGENTS_TEMPLATE_PATH = SKILL_ROOT / "references" / "agent-workspace-template.md"
ACCOUNT_AGENTS_TEMPLATE_PATH = SKILL_ROOT / "references" / "account-agent-workspace-template.md"


def agents_md_content(opportunity_name: str) -> str:
    template = AGENTS_TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("{{OPPORTUNITY_NAME}}", opportunity_name)


def ensure_account_agents_file(account_root: Path, write: bool) -> bool:
    agents_path = account_root / AGENTS_FILE_NAME
    if agents_path.is_file():
        print(f"ready: {agents_path}")
        return True
    if not write:
        print(f"missing: {agents_path}")
        return False
    agents_path.write_text(ACCOUNT_AGENTS_TEMPLATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"created: {agents_path}")
    return True


def ensure_agents_file(opportunity_path: Path, write: bool) -> bool:
    agents_path = opportunity_path / AGENTS_FILE_NAME
    if agents_path.is_file():
        print(f"ready: {agents_path}")
        return True
    if not write:
        print(f"missing: {agents_path}")
        return False
    agents_path.write_text(agents_md_content(opportunity_path.name), encoding="utf-8")
    print(f"created: {agents_path}")
    return True


def validate_opportunity_name(name: str) -> str:
    candidate = name.strip()
    if not candidate:
        raise ValueError("Opportunity name cannot be empty.")
    if candidate != name or candidate.endswith("."):
        raise ValueError("Opportunity name cannot start or end with spaces or end with a period.")
    if candidate in {".", ".."}:
        raise ValueError("Opportunity name cannot be '.' or '..'.")
    if len(candidate) > 128:
        raise ValueError("Opportunity name must be 128 characters or fewer.")
    if any(character in INVALID_NAME_CHARACTERS or ord(character) < 32 for character in candidate):
        raise ValueError(
            "Opportunity name contains characters that are unsafe for common enterprise storage or Windows."
        )
    if candidate.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        raise ValueError("Opportunity name uses a reserved Windows device name.")
    return candidate


def template_entries(template_root: Path) -> list[tuple[Path, Path]]:
    entries: list[tuple[Path, Path]] = []
    for source in sorted(template_root.rglob("*")):
        entries.append((source, Path("workspace") / source.relative_to(template_root)))
    return entries


def expected_entries(template_root: Path) -> list[tuple[Path | None, Path]]:
    entries = template_entries(template_root)
    entries.extend((None, Path(*parts)) for parts in DELIVERABLE_PATHS)
    return entries


def print_template_status(account_root: Path, opportunity_path: Path, template_root: Path) -> list[str]:
    missing: list[str] = []
    for source, relative in expected_entries(template_root):
        target = opportunity_path / relative
        expected_file = source is not None and source.is_file()
        ready = target.is_file() if expected_file else target.is_dir()
        if ready:
            print(f"ready: {target}")
        else:
            print(f"missing: {target}")
            missing.append(relative.as_posix())
    for agents_path in (account_root / AGENTS_FILE_NAME, opportunity_path / AGENTS_FILE_NAME):
        if agents_path.is_file():
            print(f"ready: {agents_path}")
        else:
            print(f"missing: {agents_path}")
            missing.append(agents_path.relative_to(account_root).as_posix())
    return missing


def copy_missing_workspace(template_root: Path, opportunity_path: Path) -> None:
    workspace_path = opportunity_path / "workspace"
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"ready: {workspace_path}")
    for source, relative in template_entries(template_root):
        target = opportunity_path / relative
        if source.is_dir():
            if not target.exists():
                target.mkdir(parents=True)
                print(f"created: {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            print(f"preserved: {target}")
            continue
        shutil.copy2(source, target)
        print(f"created: {target}")


def ensure_deliverables(opportunity_path: Path) -> None:
    for parts in DELIVERABLE_PATHS:
        target = opportunity_path.joinpath(*parts)
        if target.exists():
            print(f"ready: {target}")
        else:
            target.mkdir()
            print(f"created: {target}")


def check_local_write_readiness(path: Path) -> bool:
    if os.access(path, os.W_OK | os.X_OK):
        print(f"local write readiness: available ({path})")
        return True
    print(
        f"Local write readiness is unavailable for: {path}. "
        "Open the local working folder as the agent workspace or grant local write access.",
        file=sys.stderr,
    )
    return False


def prepare_opportunity(account_root: Path, opportunity_path: Path, template_root: Path) -> int:
    try:
        opportunity_path.mkdir(exist_ok=True)
        copy_missing_workspace(template_root, opportunity_path)
        ensure_deliverables(opportunity_path)
        ensure_account_agents_file(account_root, write=True)
        ensure_agents_file(opportunity_path, write=True)
    except OSError as error:
        print(f"Could not prepare Opportunity folder: {error}", file=sys.stderr)
        return 1
    print(f"prepared: {opportunity_path}")
    print("If this Account folder is managed by a sync client, verify its synchronization status separately.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare or resume an Opportunity folder from the standard workspace template."
    )
    parser.add_argument("--mode", choices=("new", "existing"), required=True)
    parser.add_argument("--account-root", required=True, help="Existing local or locally synced Account folder.")
    parser.add_argument("--opportunity-name", required=True)
    parser.add_argument("--workspace-template", help="Override the standard workspace template path.")
    parser.add_argument("--check-only", action="store_true", help="Report readiness without changing files.")
    args = parser.parse_args()

    try:
        opportunity_name = validate_opportunity_name(args.opportunity_name)
    except ValueError as error:
        print(f"Invalid Opportunity name: {error}", file=sys.stderr)
        return 2

    account_root = Path(args.account_root).expanduser().resolve()
    if not account_root.is_dir():
        print(f"Account folder does not exist or is not a directory: {account_root}", file=sys.stderr)
        return 2

    template_root = Path(args.workspace_template).expanduser().resolve() if args.workspace_template else DEFAULT_WORKSPACE_TEMPLATE
    if not template_root.is_dir():
        print(f"Workspace template was not found: {template_root}", file=sys.stderr)
        return 2

    opportunity_path = account_root / opportunity_name
    if args.mode == "new" and opportunity_path.exists() and not opportunity_path.is_dir():
        print(f"A non-directory already exists at the Opportunity path: {opportunity_path}", file=sys.stderr)
        return 2
    if args.mode == "existing" and not opportunity_path.is_dir():
        print(f"Existing Opportunity folder was not found: {opportunity_path}", file=sys.stderr)
        return 1

    readiness_path = account_root if args.mode == "new" and not opportunity_path.exists() else opportunity_path
    if not check_local_write_readiness(readiness_path):
        return 1

    if args.check_only:
        if opportunity_path.is_dir():
            print_template_status(account_root, opportunity_path, template_root)
        else:
            print(f"ready to create: {opportunity_path}")
        print("check complete: no folders or files were created or changed")
        return 0

    return prepare_opportunity(account_root, opportunity_path, template_root)


if __name__ == "__main__":
    raise SystemExit(main())

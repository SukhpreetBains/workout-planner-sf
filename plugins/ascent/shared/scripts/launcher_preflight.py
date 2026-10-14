"""Validate engine invocation before creating an environment. Standard library only."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def validate(arguments: list[str]) -> None:
    value = os.environ.get("ASCENT_PROJECT_ROOT", "").strip()
    if not value:
        raise ValueError("Set ASCENT_PROJECT_ROOT to the confirmed Project folder before running the workspace engine.")
    root = Path(value).expanduser()
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("ASCENT_PROJECT_ROOT must be an existing absolute Project path.")
    root = root.resolve()
    workspace = root / "workspace"
    if not all((workspace / name).is_dir() for name in ("project", "trackers", "inbox", ".system")):
        raise ValueError("The selected root lacks the prepared Project workspace. Run ascent-initial-setup first; do not use the Account root.")
    if not arguments or not Path(arguments[0]).is_file():
        raise ValueError("Pass an existing engine script path from the plugin's shared/scripts directory.")
    for index, argument in enumerate(arguments[1:], 1):
        if argument == "--root":
            if index + 1 >= len(arguments) or Path(arguments[index + 1]).resolve() != root:
                raise ValueError("--root must match ASCENT_PROJECT_ROOT.")
        elif argument.startswith("--root=") and Path(argument.split("=", 1)[1]).resolve() != root:
            raise ValueError("--root must match ASCENT_PROJECT_ROOT.")


if __name__ == "__main__":
    try:
        validate(sys.argv[1:])
    except ValueError as exc:
        print(f"Workspace launcher: {exc}", file=sys.stderr)
        raise SystemExit(2)

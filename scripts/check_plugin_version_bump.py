#!/usr/bin/env python3
"""Fail when plugin files changed relative to a base branch but the Codex version did not.

Codex reinstalls a local plugin only when the version in
plugins/ascent/.codex-plugin/plugin.json changes, so a change merged without
a new version never reaches existing installations.

Usage:
    python3 scripts/check_plugin_version_bump.py [--base origin/main]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

MANIFEST = "plugins/ascent/.codex-plugin/plugin.json"
PLUGIN_DIR = "plugins/ascent"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def version_at(ref: str) -> str | None:
    shown = git("show", f"{ref}:{MANIFEST}")
    return json.loads(shown.stdout).get("version") if shown.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="Branch the change will merge into.")
    args = parser.parse_args()

    merge_base = git("merge-base", args.base, "HEAD")
    if merge_base.returncode:
        print(f"cannot find a merge base with {args.base}: {merge_base.stderr.strip()}")
        return 2
    diff = git("diff", "--quiet", merge_base.stdout.strip(), "HEAD", "--", PLUGIN_DIR)
    if diff.returncode == 0:
        print(f"no changes under {PLUGIN_DIR}/; no version bump needed")
        return 0
    if diff.returncode != 1:
        print(f"git diff failed: {diff.stderr.strip()}")
        return 2

    base_version, head_version = version_at(args.base), version_at("HEAD")
    if base_version == head_version:
        print(f"{PLUGIN_DIR}/ changed, but the Codex version is still {head_version}, the same as "
              f"{args.base}. Existing installations would never receive this change.\n"
              f"Run `python3 scripts/refresh_codex_plugin.py` (or give {MANIFEST} a new "
              "version) and commit the result.")
        return 1
    print(f"Codex version {base_version} -> {head_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

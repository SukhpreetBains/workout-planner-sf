#!/usr/bin/env python3
"""Pull upstream Ascent updates into the registered source checkout.

Designed to run unattended on a schedule (see manage-plugin-update-schedule.py),
so it never prompts and never forces a change: it fast-forwards a clean `main`
checkout when it safely can, and otherwise logs why it skipped.

Pulling is all that is needed. Codex compares the checkout's
`.codex-plugin/plugin.json` version with its installed copy when the app
launches, and reinstalls only when they differ. A pulled update therefore
takes effect the next time the user relaunches Codex, provided the update
changed that version.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKETPLACE_NAME = "ascent"
PLUGIN_NAME = "ascent"
TRACKED_BRANCH = "main"


def codex_home() -> Path:
    value = os.environ.get("CODEX_HOME")
    return Path(value).expanduser() if value else Path.home() / ".codex"


def find_marketplace_source(config_text: str, name: str) -> str | None:
    section = re.search(
        rf'^\[marketplaces\.{re.escape(name)}\]\s*\n(.*?)(?=\n\[|\Z)',
        config_text,
        re.MULTILINE | re.DOTALL,
    )
    if not section:
        return None
    match = re.search(r'^source\s*=\s*"([^"]+)"', section.group(1), re.MULTILINE)
    return match.group(1) if match else None


def resolve_source_root(log) -> Path | None:
    config_path = codex_home() / "config.toml"
    if not config_path.is_file():
        log(f"no Codex config.toml found at {config_path}; skipping")
        return None
    source = find_marketplace_source(config_path.read_text(encoding="utf-8"), MARKETPLACE_NAME)
    if not source:
        log(f"no registered '{MARKETPLACE_NAME}' marketplace source in {config_path}; skipping")
        return None
    root = Path(source).expanduser()
    if not (root / ".git").is_dir():
        log(f"registered source is not a git checkout: {root}; skipping")
        return None
    return root


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=False, capture_output=True, text=True)


def plugin_version(root: Path) -> str:
    manifest = root / "plugins" / PLUGIN_NAME / ".codex-plugin" / "plugin.json"
    try:
        return str(json.loads(manifest.read_text(encoding="utf-8")).get("version", ""))
    except (OSError, json.JSONDecodeError):
        return ""


def check(root: Path, log) -> int:
    if git(["rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip() != TRACKED_BRANCH:
        log(f"checkout is not on '{TRACKED_BRANCH}'; skipping to avoid disturbing local work")
        return 0
    status = git(["status", "--porcelain"], root)
    if status.returncode != 0 or status.stdout.strip():
        log(f"working tree at {root} has uncommitted changes; skipping")
        return 0
    fetch = git(["fetch", "--quiet", "origin", TRACKED_BRANCH], root)
    if fetch.returncode != 0:
        log(f"git fetch failed: {fetch.stderr.strip()}")
        return 1
    before = git(["rev-parse", "HEAD"], root).stdout.strip()
    if before == git(["rev-parse", f"origin/{TRACKED_BRANCH}"], root).stdout.strip():
        log(f"already up to date at {before[:12]}")
        return 0
    old_version = plugin_version(root)
    pull = git(["pull", "--ff-only", "origin", TRACKED_BRANCH], root)
    if pull.returncode != 0:
        log(f"git pull --ff-only failed (history may have diverged): {pull.stderr.strip()}")
        return 1
    after = git(["rev-parse", "HEAD"], root).stdout.strip()
    new_version = plugin_version(root)
    log(f"pulled {before[:12]} -> {after[:12]}")
    if new_version != old_version:
        log(f"plugin version {old_version} -> {new_version}; relaunch Codex to load the update")
    else:
        plugin_changed = git(["diff", "--quiet", before, after, "--", f"plugins/{PLUGIN_NAME}"], root).returncode
        if plugin_changed:
            log(f"plugin files changed but the version is still {new_version}; Codex will not "
                "load these changes until a later update changes the version")
    return 0


def main() -> int:
    log_lines: list[str] = [f"=== {datetime.now(timezone.utc).isoformat(timespec='seconds')} ==="]
    try:
        root = resolve_source_root(log_lines.append)
        exit_code = check(root, log_lines.append) if root else 0
    except Exception as error:  # unattended background job: log, never crash silently
        log_lines.append(f"unexpected error: {error}")
        exit_code = 1

    try:
        with (codex_home() / "ascent-plugin-update.log").open("a", encoding="utf-8") as handle:
            handle.write("\n".join(log_lines) + "\n")
    except OSError:
        pass
    print("\n".join(log_lines))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

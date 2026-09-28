#!/usr/bin/env python3
"""Check the registered Ascent source checkout for upstream updates and
refresh the installed Codex plugin cache when one is found.

Designed to run unattended on a daily schedule (see
manage-plugin-update-schedule.py), so it never prompts and never forces a
change: it fast-forwards a clean `main` checkout when it safely can, and
otherwise logs why it skipped. Every step is idempotent, so a run that fails
partway (for example, `codex` was not on PATH) simply retries on the next
scheduled run.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKETPLACE_NAME = "ascent"
PLUGIN_NAME = "ascent"
TRACKED_BRANCH = "main"
CODEX_VERSION = re.compile(r"^(?P<base>[^+]+)(?:\+codex\.[a-z0-9-]+)?$")


def codex_home() -> Path:
    value = os.environ.get("CODEX_HOME")
    return Path(value).expanduser() if value else Path.home() / ".codex"


def state_path() -> Path:
    return codex_home() / "ascent-plugin-update-state.json"


def load_state() -> dict:
    path = state_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


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


def current_branch(root: Path) -> str:
    return git(["rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip()


def working_tree_clean(root: Path) -> bool:
    result = git(["status", "--porcelain"], root)
    return result.returncode == 0 and not result.stdout.strip()


def commit_hash(root: Path, ref: str = "HEAD") -> str:
    return git(["rev-parse", ref], root).stdout.strip()


def bump_cachebuster(plugin_root: Path) -> str:
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(manifest.get("version", ""))
    match = CODEX_VERSION.fullmatch(version)
    if not match:
        raise ValueError(f"unexpected version format in {manifest_path}: {version!r}")
    cachebuster = datetime.now(timezone.utc).strftime("local-%Y%m%d-%H%M%S")
    new_version = f"{match.group('base')}+codex.{cachebuster}"
    manifest["version"] = new_version
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return new_version


def restore_manifest(root: Path, manifest_path: Path) -> None:
    """codex plugin add copies the bumped manifest into a version-named
    cache directory at the moment it runs; the source checkout does not
    need to keep the bump afterward. Discard it so the working tree stays
    clean, otherwise every later run would see its own leftover edit as
    'uncommitted changes' and refuse to check for updates ever again.
    """
    git(["checkout", "--", str(manifest_path.relative_to(root))], root)


def main() -> int:
    log_lines: list[str] = []

    def log(message: str) -> None:
        log_lines.append(message)

    log(f"=== {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===")
    exit_code = 0

    try:
        root = resolve_source_root(log)
        if root is None:
            pass
        elif current_branch(root) != TRACKED_BRANCH:
            log(f"checkout is not on '{TRACKED_BRANCH}'; skipping to avoid disturbing local work")
        elif not working_tree_clean(root):
            log(f"working tree at {root} has uncommitted changes; skipping")
        else:
            fetch = git(["fetch", "--quiet", "origin", TRACKED_BRANCH], root)
            if fetch.returncode != 0:
                log(f"git fetch failed: {fetch.stderr.strip()}")
                exit_code = 1
            else:
                before = commit_hash(root)
                remote = commit_hash(root, f"origin/{TRACKED_BRANCH}")
                if before != remote:
                    pull = git(["pull", "--ff-only", "origin", TRACKED_BRANCH], root)
                    if pull.returncode != 0:
                        log(f"git pull --ff-only failed (history may have diverged): {pull.stderr.strip()}")
                        exit_code = 1

                head = commit_hash(root)
                state = load_state()
                if exit_code == 0 and state.get("last_installed_commit") == head:
                    log(f"already up to date and installed at {head[:12]}")
                elif exit_code == 0:
                    if head != before:
                        log(f"pulled {before[:12]} -> {head[:12]}")
                    plugin_root = root / "plugins" / PLUGIN_NAME
                    if not plugin_root.is_dir():
                        log(f"plugin source folder missing: {plugin_root}")
                        exit_code = 1
                    else:
                        codex_cli = shutil.which("codex")
                        if not codex_cli:
                            log("codex CLI not found on PATH; will retry the install on the next scheduled run")
                            exit_code = 1
                        else:
                            manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
                            version = bump_cachebuster(plugin_root)
                            log(f"codex manifest version: {version}")
                            install = subprocess.run(
                                [codex_cli, "plugin", "add", f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"],
                                cwd=root,
                                check=False,
                                capture_output=True,
                                text=True,
                            )
                            restore_manifest(root, manifest_path)
                            if install.returncode != 0:
                                log(f"codex plugin add failed: {install.stderr.strip()}")
                                exit_code = 1
                            else:
                                save_state({"last_installed_commit": head})
                                log("plugin reinstalled; new Codex tasks will load the update")
    except Exception as error:  # unattended background job: log, never crash silently
        log(f"unexpected error: {error}")
        exit_code = 1

    try:
        with state_path().with_name("ascent-plugin-update.log").open("a", encoding="utf-8") as handle:
            handle.write("\n".join(log_lines) + "\n")
    except OSError:
        pass
    for line in log_lines:
        print(line)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

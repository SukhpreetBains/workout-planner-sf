"""Tell the user about Ascent updates they would otherwise never see.

- A newer Ascent is downloaded but this session is still running the old one:
  Codex only reinstalls from the registered checkout when the app launches.
- The background update job is stuck: blocked by macOS privacy settings, or
  no successful check in STALE_DAYS, so updates have quietly stopped.

Read-only and silent on any doubt: it never blocks the caller.
"""

from __future__ import annotations

import json
import os
import plistlib
import re
import time
from datetime import datetime
from pathlib import Path

MARKETPLACE_NAME = "ascent"
MANIFEST = Path(".codex-plugin") / "plugin.json"
LOADED_PLUGIN_ROOT = Path(__file__).resolve().parents[2]
JOB_LOG = "ascent-plugin-update.log"
JOB_LABEL = "com.slalom.ascent.plugin-update-check"
STALE_DAYS = 10
PLAIN_REASONS = (
    ("uncommitted changes", "the Ascent folder has local changes, so updates are held back to avoid overwriting them"),
    ("is not on 'main'", "the Ascent folder is on a development branch, so updates are held back"),
    ("git fetch failed", "it couldn't reach GitHub"),
    ("git pull --ff-only failed", "the Ascent folder no longer matches GitHub's history"),
    ("config.toml", "Codex's record of where Ascent is installed couldn't be found"),
    ("not a git checkout", "the Ascent folder is no longer a git checkout"),
)


def codex_home() -> Path:
    value = os.environ.get("CODEX_HOME")
    return Path(value).expanduser() if value else Path.home() / ".codex"


def registered_plugin_root() -> Path | None:
    config = codex_home() / "config.toml"
    if not config.is_file():
        return None
    section = re.search(rf'^\[marketplaces\.{MARKETPLACE_NAME}\]\s*\n(.*?)(?=\n\[|\Z)',
                        config.read_text(encoding="utf-8"), re.MULTILINE | re.DOTALL)
    source = section and re.search(r'^source\s*=\s*"([^"]+)"', section.group(1), re.MULTILINE)
    return Path(source.group(1)).expanduser() / "plugins" / MARKETPLACE_NAME if source else None


def version_at(plugin_root: Path) -> str | None:
    try:
        return str(json.loads((plugin_root / MANIFEST).read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError):
        return None


def update_notice() -> str | None:
    try:
        source = registered_plugin_root()
        if source is None or source.resolve() == LOADED_PLUGIN_ROOT:
            return None
        on_disk, loaded = version_at(source), version_at(LOADED_PLUGIN_ROOT)
    except OSError:
        return None
    if not on_disk or not loaded or on_disk == loaded:
        return None
    return ("An Ascent update is ready. Quit and relaunch Codex to start using it "
            f"(this session is running {loaded}; {on_disk} is downloaded).")


def job_python() -> str | None:
    plist = Path.home() / "Library" / "LaunchAgents" / f"{JOB_LABEL}.plist"
    try:
        return plistlib.loads(plist.read_bytes())["ProgramArguments"][0]
    except (OSError, ValueError, KeyError, IndexError, plistlib.InvalidFileException):
        return None


def log_runs(text: str) -> list[tuple[datetime, list[str]]]:
    runs: list[tuple[datetime, list[str]]] = []
    for line in text.splitlines():
        header = re.fullmatch(r"=== (\S+) ===", line.strip())
        if header:
            try:
                runs.append((datetime.fromisoformat(header.group(1)), []))
            except ValueError:
                continue
        elif runs and line.strip():
            runs[-1][1].append(line.strip())
    return runs


def job_notice(now: float | None = None) -> str | None:
    log = codex_home() / JOB_LOG
    now = time.time() if now is None else now
    try:
        if now - log.stat().st_mtime > STALE_DAYS * 86400:
            return None
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    if any("Operation not permitted" in line for line in text.splitlines()[-5:]):
        python = job_python()
        return ("Ascent's background updates are blocked by macOS privacy settings, so no updates are "
                "being downloaded. To fix it, open System Settings > Privacy & Security > Full Disk "
                f"Access and add {python or 'the Python program that runs the Ascent update job'}.")

    runs = log_runs(text)
    if not runs:
        return None
    successes = [when for when, lines in runs
                 if any(line.startswith(("already up to date", "pulled ")) for line in lines)]
    if successes and now - max(successes).timestamp() < STALE_DAYS * 86400:
        return None
    last = runs[-1][1][-1] if runs[-1][1] else ""
    reason = next((plain for key, plain in PLAIN_REASONS if key in last), last or "the last check did not finish")
    last_ok = max(successes) if successes else None
    since = f"since {last_ok:%B} {last_ok.day}" if last_ok else "since they were set up"
    return (f"Ascent's background updates have been paused {since}: {reason}. "
            "Ask whoever set up Ascent for you to take a look.")

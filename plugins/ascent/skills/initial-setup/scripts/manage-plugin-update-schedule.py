#!/usr/bin/env python3
"""Install, check, remove, or reschedule the background job that runs
check-for-plugin-update.py.

- macOS: a per-user LaunchAgent under ~/Library/LaunchAgents/.
- Windows: a per-user Scheduled Task via schtasks.
- Linux: a best-effort per-user crontab entry.

--install is idempotent: it does nothing if the job already exists at the
requested frequency, and updates it in place (no uninstall needed) if the
requested frequency differs from what is currently installed. This script
only ever touches its own job; it never disturbs other scheduled tasks or
crontab entries.
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

JOB_LABEL = "com.slalom.ascent.plugin-update-check"
MARKETPLACE_NAME = "ascent"
TASK_NAME = "AscentPluginUpdateCheck"
CRON_MARKER = "# ascent-plugin-update-check"
FREQUENCIES = ("daily", "weekly")
DEFAULT_FREQUENCY = "daily"
MACOS_INTERVAL_SECONDS = {"daily": 86400, "weekly": 7 * 86400}
CRON_SCHEDULE = {"daily": "0 9 * * *", "weekly": "0 9 * * 0"}


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


def resolve_source_root() -> Path | None:
    config_path = codex_home() / "config.toml"
    if not config_path.is_file():
        return None
    source = find_marketplace_source(config_path.read_text(encoding="utf-8"), MARKETPLACE_NAME)
    if not source:
        return None
    root = Path(source).expanduser()
    return root if (root / ".git").is_dir() else None


def is_git_sourced_install() -> bool:
    """True when this install's plugin content comes from Codex's own
    Git-subdir marketplace refresh rather than a local checkout this job
    could pull. Checked by walking up from this script's own location,
    since that is exactly where Codex loaded the running plugin from: a
    Git-subdir clone (codex-rs/core-plugins/src/loader.rs) has no `.git` of
    its own anywhere above it, while a local-source install's `__file__`
    sits inside the registered checkout.
    """
    return not any((parent / ".git").is_dir() for parent in Path(__file__).resolve().parents)


def check_script_path(root: Path) -> Path:
    return root / "plugins" / "ascent" / "skills" / "initial-setup" / "scripts" / "check-for-plugin-update.py"


# ---- macOS: LaunchAgent ----

def launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{JOB_LABEL}.plist"


def macos_status() -> bool:
    return launch_agent_path().is_file()


def macos_current_frequency() -> str | None:
    plist_path = launch_agent_path()
    if not plist_path.is_file():
        return None
    match = re.search(
        r"<key>StartInterval</key>\s*<integer>(\d+)</integer>", plist_path.read_text(encoding="utf-8")
    )
    if not match:
        return None
    seconds = int(match.group(1))
    for name, value in MACOS_INTERVAL_SECONDS.items():
        if value == seconds:
            return name
    return f"every {seconds}s"


def macos_install(script_path: Path, python_exe: str, frequency: str) -> None:
    plist_path = launch_agent_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    path_env = os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    log_path = codex_home() / "ascent-plugin-update.log"
    interval = MACOS_INTERVAL_SECONDS[frequency]
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{JOB_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>{script_path}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{path_env}</string>
    </dict>
    <key>StartInterval</key>
    <integer>{interval}</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>
"""
    plist_path.write_text(plist, encoding="utf-8")
    subprocess.run(["launchctl", "unload", str(plist_path)], check=False, capture_output=True)
    result = subprocess.run(
        ["launchctl", "load", "-w", str(plist_path)], check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"launchctl load failed: {result.stderr.strip()}")


def macos_uninstall() -> None:
    plist_path = launch_agent_path()
    if plist_path.is_file():
        subprocess.run(["launchctl", "unload", str(plist_path)], check=False, capture_output=True)
        plist_path.unlink()


def macos_full_disk_access_warning(python_exe: str) -> str | None:
    """RunAtLoad fires the job immediately on install. macOS sandboxes
    launchd-spawned processes separately from interactive shells: a python
    binary that reads a repository fine from Terminal can still be denied
    access under launchd when that repository lives under a
    TCC-protected location (Desktop, Documents, iCloud Drive, or a
    provider-synced folder such as OneDrive or Dropbox under
    ~/Library/CloudStorage). Check the job's own log for that specific
    failure so it is disclosed immediately instead of failing silently,
    every day, forever.
    """
    log_path = codex_home() / "ascent-plugin-update.log"
    for _ in range(10):
        if log_path.is_file():
            break
        time.sleep(0.3)
    else:
        return None
    time.sleep(0.5)
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return None
    blocks = text.split("=== ")
    last_block = blocks[-1] if blocks else ""
    if "operation not permitted" not in last_block.lower():
        return None
    return (
        "The update-check job installed, but its very first run could not read "
        "the repository — macOS blocked the background process, most likely "
        "because this checkout lives under a privacy-protected or "
        "cloud-synced folder (Desktop, Documents, iCloud Drive, OneDrive, or "
        "similar). To fix it: open System Settings > Privacy & Security > "
        f"Full Disk Access, click +, and add this Python: {python_exe}. The "
        "job is still installed and will start working once access is "
        "granted; nothing else needs to change."
    )


# ---- Windows: Scheduled Task ----

def windows_status() -> bool:
    result = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME], check=False, capture_output=True, text=True
    )
    return result.returncode == 0


def windows_current_frequency() -> str | None:
    result = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "list", "/v"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    match = re.search(r"^Schedule Type:\s*(.+)$", result.stdout, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip().lower()
    return value if value in FREQUENCIES else value


def windows_install(script_path: Path, python_exe: str, frequency: str) -> None:
    command = f'"{python_exe}" "{script_path}"'
    args = ["schtasks", "/create", "/tn", TASK_NAME, "/tr", command, "/sc", frequency, "/st", "09:00", "/f"]
    if frequency == "weekly":
        args += ["/d", "SUN"]
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"schtasks /create failed: {result.stderr.strip()}")


def windows_uninstall() -> None:
    subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"], check=False, capture_output=True)


# ---- Linux: crontab (best effort) ----

def _linux_crontab_lines() -> list[str]:
    result = subprocess.run(["crontab", "-l"], check=False, capture_output=True, text=True)
    return result.stdout.splitlines() if result.returncode == 0 else []


def _linux_strip_marker(lines: list[str]) -> list[str]:
    filtered: list[str] = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if CRON_MARKER in line:
            skip_next = True
            continue
        filtered.append(line)
    return filtered


def linux_status() -> bool:
    return any(CRON_MARKER in line for line in _linux_crontab_lines())


def linux_current_frequency() -> str | None:
    lines = _linux_crontab_lines()
    for index, line in enumerate(lines):
        if CRON_MARKER in line and index + 1 < len(lines):
            entry = lines[index + 1]
            for name, schedule in CRON_SCHEDULE.items():
                if entry.startswith(schedule):
                    return name
            return "custom schedule"
    return None


def linux_install(script_path: Path, python_exe: str, frequency: str) -> None:
    lines = _linux_strip_marker(_linux_crontab_lines())
    lines.append(CRON_MARKER)
    lines.append(f'{CRON_SCHEDULE[frequency]} "{python_exe}" "{script_path}"')
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", check=True, text=True)


def linux_uninstall() -> None:
    raw = _linux_crontab_lines()
    filtered = _linux_strip_marker(raw)
    if filtered == raw:
        return
    subprocess.run(
        ["crontab", "-"], input="\n".join(filtered) + ("\n" if filtered else ""), check=True, text=True
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--install", action="store_true", help="Create the job, or update it to --frequency if already installed."
    )
    group.add_argument("--status", action="store_true", help="Report whether the job is installed and how often it runs.")
    group.add_argument("--uninstall", action="store_true", help="Remove the job.")
    parser.add_argument(
        "--frequency",
        choices=FREQUENCIES,
        help=f"How often to check for updates (default: {DEFAULT_FREQUENCY}). Only used with --install.",
    )
    args = parser.parse_args()

    system = platform.system()
    if system == "Darwin":
        status_fn, frequency_fn, install_fn, uninstall_fn = (
            macos_status,
            macos_current_frequency,
            macos_install,
            macos_uninstall,
        )
    elif system == "Windows":
        status_fn, frequency_fn, install_fn, uninstall_fn = (
            windows_status,
            windows_current_frequency,
            windows_install,
            windows_uninstall,
        )
    elif system == "Linux":
        status_fn, frequency_fn, install_fn, uninstall_fn = (
            linux_status,
            linux_current_frequency,
            linux_install,
            linux_uninstall,
        )
    else:
        print(f"Unsupported platform: {system}", file=sys.stderr)
        return 2

    if args.uninstall:
        uninstall_fn()
        print("Plugin-update check removed.")
        return 0

    if not args.install:
        if is_git_sourced_install():
            print(
                "not applicable (Git-sourced install; Codex refreshes this plugin "
                "automatically on relaunch, no job needed)"
            )
        elif status_fn():
            current = frequency_fn()
            print(f"installed ({current})" if current else "installed")
        else:
            print("not installed")
        return 0

    requested = args.frequency or DEFAULT_FREQUENCY
    was_installed = status_fn()
    if was_installed:
        current = frequency_fn()
        if current == requested:
            print(f"Plugin-update check is already installed ({requested}); nothing to do.")
            return 0

    if is_git_sourced_install():
        print(
            "This is a Git-sourced install: Codex already refreshes the plugin "
            "automatically on relaunch, so there is nothing for this job to do.",
            file=sys.stderr,
        )
        return 1

    root = resolve_source_root()
    if root is None:
        print(
            "Could not resolve the Ascent source checkout from "
            f"{codex_home() / 'config.toml'}. Install the plugin from a local git "
            "checkout before scheduling update checks.",
            file=sys.stderr,
        )
        return 1

    script_path = check_script_path(root)
    if not script_path.is_file():
        print(f"check-for-plugin-update.py not found at {script_path}", file=sys.stderr)
        return 1

    try:
        install_fn(script_path, sys.executable, requested)
    except RuntimeError as error:
        print(f"Could not install the update-check job: {error}", file=sys.stderr)
        return 1

    if was_installed:
        print(f"Plugin-update check frequency changed to {requested}.")
    else:
        print(f"Plugin-update check installed ({requested}, runs {script_path}).")
    if system == "Darwin":
        warning = macos_full_disk_access_warning(sys.executable)
        if warning:
            print(f"\nACTION NEEDED: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

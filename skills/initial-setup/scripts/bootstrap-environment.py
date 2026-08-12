#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolStatus:
    label: str
    command: str
    installed: bool
    version: str | None = None


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False)


def first_line(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None
    return stripped.splitlines()[0]


def os_name() -> str:
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    if system == "Linux":
        return "linux"
    return "unknown"


def current_python_status() -> ToolStatus:
    version = first_line(sys.version.replace("\n", " "))
    return ToolStatus("Python 3", sys.executable, True, version)


def command_status(command: str, label: str) -> ToolStatus:
    resolved = shutil.which(command)
    if not resolved:
        return ToolStatus(label, command, False)

    result = run_command([command, "--version"])
    version = first_line(result.stdout) or first_line(result.stderr)
    return ToolStatus(label, command, True, version)


def collect_statuses() -> list[ToolStatus]:
    return [
        current_python_status(),
        command_status("node", "Node.js"),
        command_status("npm.cmd" if os_name() == "windows" else "npm", "npm"),
    ]


def print_statuses(statuses: list[ToolStatus]) -> None:
    print("Checking local discovery environment...")
    print()
    for status in statuses:
        if status.installed:
            if status.version:
                print(f"[ok] {status.label}: {status.version}")
            else:
                print(f"[ok] {status.label}: installed")
        else:
            print(f"[missing] {status.label} ({status.command})")


def install_with_brew(formula: str) -> bool:
    return run_command(["brew", "install", formula]).returncode == 0


def install_with_winget(package_id: str) -> bool:
    return (
        run_command(
            [
                "winget",
                "install",
                "--id",
                package_id,
                "--exact",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        ).returncode
        == 0
    )


def install_missing() -> tuple[bool, list[str]]:
    platform_name = os_name()
    notes: list[str] = []
    attempted_install = False

    statuses = {status.label: status for status in collect_statuses()}

    if not statuses["Node.js"].installed or not statuses["npm"].installed:
        attempted_install = True
        if platform_name == "macos" and shutil.which("brew"):
            if install_with_brew("node"):
                notes.append("Installed Node.js and npm with Homebrew.")
            else:
                notes.append("Could not install Node.js with Homebrew.")
        elif platform_name == "windows" and shutil.which("winget"):
            if install_with_winget("OpenJS.NodeJS.LTS"):
                notes.append("Installed Node.js and npm with winget.")
            else:
                notes.append("Could not install Node.js with winget.")
        else:
            notes.append(
                f"No supported automatic Node.js installer is configured for {platform_name}."
            )

    return attempted_install, notes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check and optionally install the discovery environment baseline."
    )
    parser.add_argument(
        "--install-missing",
        action="store_true",
        help="Install supported missing dependencies using the platform package manager.",
    )
    args = parser.parse_args()

    statuses = collect_statuses()
    print_statuses(statuses)

    if args.install_missing:
        attempted_install, notes = install_missing()
        if notes:
            print()
            for note in notes:
                print(f"- {note}")
        if attempted_install:
            print()
            print("Rechecking environment after installation attempts...")
            print()
            statuses = collect_statuses()
            print_statuses(statuses)

    missing = [status for status in statuses if not status.installed]
    print()
    if missing:
        print("Environment baseline is incomplete.")
        return 1

    print("Environment baseline is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

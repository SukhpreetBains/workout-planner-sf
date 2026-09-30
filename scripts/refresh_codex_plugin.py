#!/usr/bin/env python3
"""Refresh the local Ascent plugin for Codex.

On a clean `main` checkout (how end users run Ascent) this only pulls the
latest release; relaunching Codex then installs it. On any other branch, or
with uncommitted changes (a developer iterating), it gives the plugin a new
version and reinstalls it so the local edits load; commit that version bump
with the change.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLUGIN = "ascent"
DEFAULT_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
CODEX_VERSION = re.compile(r"^(?P<base>[^+]+)(?:\+codex\.[a-z0-9-]+)?$")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def find_marketplace_entry(marketplace: dict, plugin_name: str) -> dict:
    for entry in marketplace.get("plugins", []):
        if entry.get("name") == plugin_name:
            return entry
    raise SystemExit(f"plugin {plugin_name!r} is not listed in the marketplace")


def resolve_plugin_root(marketplace_path: Path, entry: dict) -> Path:
    source = entry.get("source")
    if not isinstance(source, dict):
        raise SystemExit("marketplace entry must use a source object")
    if source.get("source") != "local":
        raise SystemExit(
            "this helper only refreshes local Codex marketplace plugins; "
            f"found source {source.get('source')!r}"
        )
    source_path = source.get("path")
    if not source_path:
        raise SystemExit("marketplace entry is missing source.path")
    return (marketplace_path.parent.parent.parent / source_path).resolve()


def update_cachebuster(plugin_root: Path, dry_run: bool) -> str:
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path)
    version = str(manifest.get("version", ""))
    match = CODEX_VERSION.fullmatch(version)
    if not match:
        raise SystemExit(
            f"{manifest_path} version must be a base version with at most one +codex suffix"
        )
    cachebuster = datetime.now(timezone.utc).strftime("local-%Y%m%d-%H%M%S")
    new_version = f"{match.group('base')}+codex.{cachebuster}"
    if not dry_run:
        manifest["version"] = new_version
        save_json(manifest_path, manifest)
    return new_version


def run_codex_install(plugin_ref: str, dry_run: bool) -> None:
    command = ["codex", "plugin", "add", plugin_ref]
    print("+ " + " ".join(command))
    if dry_run:
        return
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        raise SystemExit("codex CLI was not found on PATH") from None
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def is_release_checkout(plugin_root: Path) -> bool:
    """A clean checkout of `main`: an end user's install, not a developer's work in progress."""
    branch = git(plugin_root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    status = git(plugin_root, "status", "--porcelain")
    return branch == "main" and status.returncode == 0 and not status.stdout.strip()


def pull_latest_release(plugin_root: Path, dry_run: bool) -> int:
    print("Clean main checkout: pulling the latest release without changing the local version.")
    print("+ git pull --ff-only origin main")
    if dry_run:
        print("Dry run complete. Nothing was pulled.")
        return 0
    before = git(plugin_root, "rev-parse", "HEAD").stdout.strip()
    pull = git(plugin_root, "pull", "--ff-only", "origin", "main")
    if pull.returncode:
        raise SystemExit(f"git pull failed: {pull.stderr.strip()}")
    after = git(plugin_root, "rev-parse", "HEAD").stdout.strip()
    if before == after:
        print("Already up to date.")
    else:
        print(f"Updated {before[:12]} -> {after[:12]}. Quit and relaunch the Codex app to start using it.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", default=DEFAULT_PLUGIN, help="Marketplace plugin name")
    parser.add_argument(
        "--marketplace",
        type=Path,
        default=DEFAULT_MARKETPLACE,
        help="Path to the Codex marketplace.json file",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show actions without changing files")
    args = parser.parse_args()

    marketplace_path = args.marketplace.expanduser().resolve()
    marketplace = load_json(marketplace_path)
    marketplace_name = marketplace.get("name")
    if not marketplace_name:
        raise SystemExit(f"{marketplace_path} is missing marketplace name")

    entry = find_marketplace_entry(marketplace, args.plugin)
    plugin_root = resolve_plugin_root(marketplace_path, entry)
    if not plugin_root.is_dir():
        raise SystemExit(f"plugin source folder does not exist: {plugin_root}")

    plugin_ref = f"{args.plugin}@{marketplace_name}"
    print(f"Marketplace: {marketplace_name} ({marketplace_path})")
    print(f"Plugin source: {plugin_root}")
    if is_release_checkout(plugin_root):
        return pull_latest_release(plugin_root, args.dry_run)
    version = update_cachebuster(plugin_root, args.dry_run)
    print(f"Codex manifest version: {version}")
    run_codex_install(plugin_ref, args.dry_run)
    if args.dry_run:
        print("Dry run complete. No files were changed and the plugin was not reinstalled.")
    else:
        print("Refresh complete. Restart the Codex app to load the updated plugin.")
        print("Commit the plugin.json version change with your plugin changes: Codex only "
              "reinstalls a local plugin when its version changes, so this bump is how "
              "other installs pick the changes up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Refresh the installed Codex cache for the local Ascent plugin."""

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


def restore_manifest(plugin_root: Path) -> None:
    """codex plugin add copies the bumped manifest into a version-named
    cache directory at the moment it runs; the source checkout does not
    need to keep the cachebuster afterward. Discard it so the working tree
    stays clean and the meaningless timestamp never has to be committed
    or manually discarded by hand.
    """
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    subprocess.run(["git", "checkout", "--", str(manifest_path)], cwd=plugin_root, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update the local Ascent Codex cachebuster and reinstall the plugin."
    )
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
    version = update_cachebuster(plugin_root, args.dry_run)
    print(f"Codex manifest version: {version}")
    try:
        run_codex_install(plugin_ref, args.dry_run)
    finally:
        if not args.dry_run:
            restore_manifest(plugin_root)
    if args.dry_run:
        print("Dry run complete. No files were changed and the plugin was not reinstalled.")
    else:
        print("Refresh complete. Start a new Codex task to load the updated plugin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

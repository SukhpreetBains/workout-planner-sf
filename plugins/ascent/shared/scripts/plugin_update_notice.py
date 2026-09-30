"""Tell the user when a newer Ascent is on disk than the one this session loaded.

Codex runs Ascent from its own cached copy and only reinstalls from the
registered checkout when the app launches. After a pull, the checkout can hold
a newer version than the session is using until the user relaunches Codex.
Read-only and silent on any doubt: it never blocks the caller.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

MARKETPLACE_NAME = "ascent"
MANIFEST = Path(".codex-plugin") / "plugin.json"
LOADED_PLUGIN_ROOT = Path(__file__).resolve().parents[2]


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

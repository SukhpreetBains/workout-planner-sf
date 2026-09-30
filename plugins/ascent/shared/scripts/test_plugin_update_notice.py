"""The setup check tells the user when a newer Ascent is downloaded but not yet loaded.

Run with the project environment:
    plugins/ascent/shared/scripts/py -m unittest discover -s plugins/ascent/shared/scripts
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
LOADED_ROOT = SCRIPTS.parents[1]
LOADED_VERSION = json.loads((LOADED_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


class PluginUpdateNoticeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.codex_home, self.checkout = base / "codex-home", base / "checkout"
        self.codex_home.mkdir()
        self.env = {**os.environ, "CODEX_HOME": str(self.codex_home), "ASCENT_OPPORTUNITY_ROOT": str(base)}
        os.environ["CODEX_HOME"] = str(self.codex_home)
        sys.modules.pop("plugin_update_notice", None)
        sys.path.insert(0, str(SCRIPTS))
        self.notice = importlib.import_module("plugin_update_notice")

    def tearDown(self):
        os.environ.pop("CODEX_HOME", None)
        self.tmp.cleanup()

    def register(self, source: Path, version: str | None = None) -> None:
        (self.codex_home / "config.toml").write_text(
            f'[marketplaces.ascent]\nsource_type = "local"\nsource = "{source}"\n', encoding="utf-8")
        if version:
            manifest = source / "plugins" / "ascent" / ".codex-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps({"version": version}), encoding="utf-8")

    def test_newer_download_produces_a_relaunch_notice(self):
        self.register(self.checkout, "0.1.0+codex.local-99999999-999999")
        message = self.notice.update_notice()
        self.assertIn("Quit and relaunch Codex", message)
        self.assertIn(LOADED_VERSION, message)

    def test_same_version_is_silent(self):
        self.register(self.checkout, LOADED_VERSION)
        self.assertIsNone(self.notice.update_notice())

    def test_running_straight_from_the_checkout_is_silent(self):
        self.register(LOADED_ROOT.parents[1])
        self.assertIsNone(self.notice.update_notice())

    def test_no_codex_registration_is_silent(self):
        self.assertIsNone(self.notice.update_notice())

    def test_setup_check_prints_the_notice(self):
        self.register(self.checkout, "0.1.0+codex.local-99999999-999999")
        out = subprocess.run([sys.executable, str(SCRIPTS / "sync.py"), "--check-setup"],
                             capture_output=True, text=True, env=self.env, check=True).stdout
        self.assertIn("ascent update: An Ascent update is ready.", out)


if __name__ == "__main__":
    unittest.main()

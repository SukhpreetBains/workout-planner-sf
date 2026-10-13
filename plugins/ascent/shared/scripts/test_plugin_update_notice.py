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
import time
import unittest
from datetime import datetime, timezone
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
        self.env = {**os.environ, "CODEX_HOME": str(self.codex_home), "ASCENT_PROJECT_ROOT": str(base)}
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

    def job_log(self, text: str, age_days: float = 0) -> float:
        log = self.codex_home / "ascent-plugin-update.log"
        log.write_text(text, encoding="utf-8")
        now = time.time()
        os.utime(log, (now - age_days * 86400, now - age_days * 86400))
        return now

    @staticmethod
    def run_at(days_ago: float, *lines: str) -> str:
        stamp = datetime.fromtimestamp(time.time() - days_ago * 86400, timezone.utc).isoformat(timespec="seconds")
        return f"=== {stamp} ===\n" + "".join(f"{line}\n" for line in lines)

    def test_no_job_log_is_silent(self):
        self.assertIsNone(self.notice.job_notice())

    def test_macos_permission_block_explains_the_fix(self):
        now = self.job_log("python3: can't open file '/x/check.py': [Errno 1] Operation not permitted\n")
        message = self.notice.job_notice(now)
        self.assertIn("blocked by macOS privacy settings", message)
        self.assertIn("Full Disk Access", message)

    def test_recent_successful_check_is_silent(self):
        now = self.job_log(self.run_at(1, "already up to date at abc123"))
        self.assertIsNone(self.notice.job_notice(now))

    def test_long_paused_job_explains_why_in_plain_words(self):
        now = self.job_log(self.run_at(20, "already up to date at abc123")
                           + self.run_at(1, "working tree at /x has uncommitted changes; skipping"))
        message = self.notice.job_notice(now)
        self.assertIn("paused since", message)
        self.assertIn("local changes", message)
        self.assertNotIn("working tree", message)

    def test_job_that_never_succeeded_is_reported(self):
        now = self.job_log(self.run_at(1, "git fetch failed: could not resolve host"))
        self.assertIn("since they were set up: it couldn't reach GitHub", self.notice.job_notice(now))

    def test_job_that_stopped_running_is_silent(self):
        now = self.job_log(self.run_at(30, "git fetch failed: offline"), age_days=30)
        self.assertIsNone(self.notice.job_notice(now))

    def test_setup_check_prints_the_notice(self):
        self.register(self.checkout, "0.1.0+codex.local-99999999-999999")
        out = subprocess.run([sys.executable, str(SCRIPTS / "sync.py"), "--check-setup"],
                             capture_output=True, text=True, env=self.env, check=True).stdout
        self.assertIn("ascent update: An Ascent update is ready.", out)


if __name__ == "__main__":
    unittest.main()

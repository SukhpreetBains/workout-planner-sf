"""The scheduled-update-job manager recognizes a Git-sourced install and skips it."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "ascent" / "skills" / "initial-setup" / "scripts" / "manage-plugin-update-schedule.py"


class PluginUpdateScheduleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_status(self, script: Path, codex_home: Path) -> str:
        result = subprocess.run(
            [sys.executable, str(script), "--status"],
            capture_output=True, text=True,
            env={**os.environ, "CODEX_HOME": str(codex_home)},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_git_sourced_install_reports_not_applicable(self):
        # A Git-subdir clone has no `.git` anywhere above the running script
        # (codex-rs/core-plugins/src/loader.rs strips it before caching).
        base = Path(self.tmp.name) / "cache" / "ascent" / "ascent" / "0.1.0+codex.local-1"
        script_copy = base / "skills" / "initial-setup" / "scripts" / "manage-plugin-update-schedule.py"
        script_copy.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, script_copy)
        codex_home = Path(self.tmp.name) / "codex-home"
        codex_home.mkdir()
        out = self.run_status(script_copy, codex_home)
        self.assertIn("not applicable", out)
        self.assertIn("Codex refreshes this plugin automatically", out)

    def test_local_checkout_install_is_unaffected(self):
        # Run from the real repo checkout (has .git above it): the new
        # Git-sourced detection must not fire here, whatever this machine's
        # real OS job state happens to be.
        out = self.run_status(SCRIPT, Path(self.tmp.name))
        self.assertNotIn("not applicable", out)


if __name__ == "__main__":
    unittest.main()

"""The refresh script pulls and auto-switches back to the real plugin on a clean main checkout."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "refresh_codex_plugin.py"
MANIFEST = Path("plugins/ascent/.codex-plugin/plugin.json")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


class RefreshCodexPluginTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.origin, self.editor, self.clone = base / "origin.git", base / "editor", base / "clone"
        git(base, "init", "--quiet", "--bare", "-b", "main", str(self.origin))
        git(base, "clone", "--quiet", str(self.origin), str(self.editor))
        self.write(".agents/plugins/marketplace.json", json.dumps({
            "name": "ascent-dev", "plugins": [{"name": "ascent", "source": {"source": "local", "path": "./plugins/ascent"}}]}))
        self.write(str(MANIFEST), json.dumps({"version": "0.1.0+codex.local-1"}, indent=2) + "\n")
        self.publish("release 1")
        git(base, "clone", "--quiet", str(self.origin), str(self.clone))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative: str, text: str) -> None:
        path = self.editor / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def publish(self, message: str) -> None:
        git(self.editor, "add", "-A")
        git(self.editor, "commit", "--quiet", "-m", message)
        git(self.editor, "push", "--quiet", "origin", "HEAD:main")

    def refresh(self, *args: str, env: dict | None = None) -> str:
        result = subprocess.run([sys.executable, str(SCRIPT), "--marketplace",
                                 str(self.clone / ".agents/plugins/marketplace.json"), *args],
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def version(self) -> str:
        return json.loads((self.clone / MANIFEST).read_text(encoding="utf-8"))["version"]

    def install_fake_codex(self) -> tuple[Path, Path]:
        """A fake `codex` on PATH: `remove` always fails, `add` always succeeds."""
        bin_dir = Path(self.tmp.name) / "fakebin"
        bin_dir.mkdir(exist_ok=True)
        log_path = Path(self.tmp.name) / "codex-calls.log"
        codex_path = bin_dir / "codex"
        codex_path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, pathlib\n"
            f"pathlib.Path({str(log_path)!r}).open('a').write(' '.join(sys.argv[1:]) + chr(10))\n"
            "sys.exit(1 if sys.argv[1:3] == ['plugin', 'remove'] else 0)\n",
            encoding="utf-8",
        )
        codex_path.chmod(codex_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return bin_dir, log_path

    def fake_codex_env(self, bin_dir: Path) -> dict:
        return {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}

    def test_clean_main_pulls_the_release_and_auto_switches_back(self):
        self.write(str(MANIFEST), json.dumps({"version": "0.1.0+codex.local-2"}, indent=2) + "\n")
        self.publish("release 2")
        bin_dir, log_path = self.install_fake_codex()
        out = self.refresh(env=self.fake_codex_env(bin_dir))
        self.assertIn("Quit and relaunch the Codex app", out)
        self.assertIn("Switching back to the real plugin: ascent@ascent", out)
        self.assertEqual(self.version(), "0.1.0+codex.local-2")
        self.assertEqual(git(self.clone, "status", "--porcelain"), "")
        calls = log_path.read_text(encoding="utf-8").splitlines()
        self.assertIn("plugin remove ascent@ascent-dev", calls)
        self.assertIn("plugin add ascent@ascent", calls)
        self.assertIn("Already up to date.", self.refresh(env=self.fake_codex_env(bin_dir)))

    def test_leftover_version_edit_on_main_is_restored_then_pulled(self):
        (self.clone / MANIFEST).write_text(
            json.dumps({"version": "0.1.0+codex.local-LOCAL"}, indent=2) + "\n", encoding="utf-8")
        self.write(str(MANIFEST), json.dumps({"version": "0.1.0+codex.local-2"}, indent=2) + "\n")
        self.publish("release 2")
        bin_dir, _ = self.install_fake_codex()
        out = self.refresh(env=self.fake_codex_env(bin_dir))
        self.assertIn("Restoring a leftover local version edit", out)
        self.assertIn("Quit and relaunch the Codex app", out)
        self.assertEqual(self.version(), "0.1.0+codex.local-2")
        self.assertEqual(git(self.clone, "status", "--porcelain"), "")

    def test_feature_branch_takes_the_developer_path(self):
        git(self.clone, "checkout", "--quiet", "-b", "feature/x")
        out = self.refresh("--dry-run")
        self.assertIn("Codex manifest version: 0.1.0+codex.local-", out)
        self.assertNotIn("git pull", out)

    def test_uncommitted_changes_take_the_developer_path(self):
        (self.clone / "plugins/ascent/NOTES.md").write_text("work in progress", encoding="utf-8")
        out = self.refresh("--dry-run")
        self.assertIn("Codex manifest version: 0.1.0+codex.local-", out)
        self.assertNotIn("git pull", out)

    def test_preview_dry_run_also_shows_removing_the_real_plugin(self):
        git(self.clone, "checkout", "--quiet", "-b", "feature/x")
        out = self.refresh("--dry-run")
        self.assertIn("codex plugin add ascent@ascent-dev", out)
        self.assertIn("codex plugin remove ascent@ascent", out)

    def test_release_dry_run_removes_sandbox_and_installs_real(self):
        out = self.refresh("--dry-run", "--release")
        self.assertIn("Switching back to the real plugin: ascent@ascent", out)
        self.assertIn("codex plugin remove ascent@ascent-dev", out)
        self.assertIn("codex plugin add ascent@ascent", out)

    def test_preview_removes_the_real_plugin_best_effort_when_not_installed(self):
        git(self.clone, "checkout", "--quiet", "-b", "feature/x")
        bin_dir, log_path = self.install_fake_codex()
        out = self.refresh(env=self.fake_codex_env(bin_dir))
        self.assertIn("Nothing to remove for ascent@ascent", out)
        calls = log_path.read_text(encoding="utf-8").splitlines()
        self.assertIn("plugin add ascent@ascent-dev", calls)
        self.assertIn("plugin remove ascent@ascent", calls)

    def test_release_removes_sandbox_best_effort_and_installs_real(self):
        bin_dir, log_path = self.install_fake_codex()
        out = self.refresh("--release", env=self.fake_codex_env(bin_dir))
        self.assertIn("Nothing to remove for ascent@ascent-dev", out)
        self.assertIn("Restart the Codex app to load the real plugin.", out)
        calls = log_path.read_text(encoding="utf-8").splitlines()
        self.assertIn("plugin remove ascent@ascent-dev", calls)
        self.assertIn("plugin add ascent@ascent", calls)


if __name__ == "__main__":
    unittest.main()

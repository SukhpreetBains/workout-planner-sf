"""The scheduled update job pulls safely and reports whether Codex will load the pull."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "ascent" / "skills" / "initial-setup" / "scripts" / "check-for-plugin-update.py"
MANIFEST = Path("plugins/ascent/.codex-plugin/plugin.json")
SKILL = Path("plugins/ascent/skills/example/SKILL.md")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


class PluginUpdateCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.origin, self.clone, self.editor = base / "origin.git", base / "clone", base / "editor"
        git(base, "init", "--quiet", "--bare", "-b", "main", str(self.origin))
        git(base, "clone", "--quiet", str(self.origin), str(self.editor))
        self.write(MANIFEST, json.dumps({"version": "0.1.0+codex.local-1"}))
        self.write(SKILL, "first")
        self.publish("init")
        git(base, "clone", "--quiet", str(self.origin), str(self.clone))
        self.codex_home = base / "codex-home"
        self.codex_home.mkdir()
        (self.codex_home / "config.toml").write_text(
            f'[marketplaces.ascent]\nsource_type = "local"\nsource = "{self.clone}"\n', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative: Path, text: str) -> None:
        path = self.editor / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def publish(self, message: str) -> None:
        git(self.editor, "add", "-A")
        git(self.editor, "commit", "--quiet", "-m", message)
        git(self.editor, "push", "--quiet", "origin", "HEAD:main")

    def run_check(self) -> str:
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True,
                                env={**os.environ, "CODEX_HOME": str(self.codex_home)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_pull_with_new_version_asks_for_relaunch(self):
        self.write(SKILL, "second")
        self.write(MANIFEST, json.dumps({"version": "0.1.0+codex.local-2"}))
        self.publish("update with version bump")
        out = self.run_check()
        self.assertIn("plugin version 0.1.0+codex.local-1 -> 0.1.0+codex.local-2; relaunch Codex", out)
        self.assertEqual((self.clone / SKILL).read_text(encoding="utf-8"), "second")
        self.assertEqual(git(self.clone, "status", "--porcelain"), "")
        self.assertIn("already up to date", self.run_check())

    def test_pull_without_version_bump_warns(self):
        self.write(SKILL, "second")
        self.publish("update without version bump")
        out = self.run_check()
        self.assertIn("plugin files changed but the version is still 0.1.0+codex.local-1", out)

    def manifest(self, version: str, description: str = "Ascent") -> str:
        return json.dumps({"name": "ascent", "version": version, "description": description}, indent=2) + "\n"

    def test_leftover_version_edit_is_restored_and_update_proceeds(self):
        self.write(MANIFEST, self.manifest("0.1.0+codex.local-1"))
        self.publish("multi-line manifest")
        self.run_check()
        (self.clone / MANIFEST).write_text(self.manifest("0.1.0+codex.local-LOCAL"), encoding="utf-8")
        self.write(SKILL, "second")
        self.write(MANIFEST, self.manifest("0.1.0+codex.local-2"))
        self.publish("release 2")
        out = self.run_check()
        self.assertIn("restored a leftover local version edit", out)
        self.assertIn("plugin version 0.1.0+codex.local-1 -> 0.1.0+codex.local-2", out)
        self.assertEqual(git(self.clone, "status", "--porcelain"), "")

    def test_other_local_manifest_edits_still_block_updates(self):
        self.write(MANIFEST, self.manifest("0.1.0+codex.local-1"))
        self.publish("multi-line manifest")
        self.run_check()
        (self.clone / MANIFEST).write_text(self.manifest("0.1.0+codex.local-1", "edited locally"), encoding="utf-8")
        self.assertIn("uncommitted changes; skipping", self.run_check())

    def test_skips_dirty_tree_and_other_branches(self):
        (self.clone / SKILL).write_text("local edit", encoding="utf-8")
        self.assertIn("uncommitted changes; skipping", self.run_check())
        git(self.clone, "checkout", "--quiet", "--", str(SKILL))
        git(self.clone, "checkout", "--quiet", "-b", "feature/x")
        self.assertIn("not on 'main'; skipping", self.run_check())


if __name__ == "__main__":
    unittest.main()

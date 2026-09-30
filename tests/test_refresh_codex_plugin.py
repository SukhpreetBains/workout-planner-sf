"""The refresh script only pulls on an end user's clean main checkout."""

from __future__ import annotations

import json
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
            "name": "ascent", "plugins": [{"name": "ascent", "source": {"source": "local", "path": "./plugins/ascent"}}]}))
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

    def refresh(self, *args: str) -> str:
        result = subprocess.run([sys.executable, str(SCRIPT), "--marketplace",
                                 str(self.clone / ".agents/plugins/marketplace.json"), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def version(self) -> str:
        return json.loads((self.clone / MANIFEST).read_text(encoding="utf-8"))["version"]

    def test_clean_main_pulls_the_release_without_a_local_version(self):
        self.write(str(MANIFEST), json.dumps({"version": "0.1.0+codex.local-2"}, indent=2) + "\n")
        self.publish("release 2")
        out = self.refresh()
        self.assertIn("Quit and relaunch the Codex app", out)
        self.assertEqual(self.version(), "0.1.0+codex.local-2")
        self.assertEqual(git(self.clone, "status", "--porcelain"), "")
        self.assertIn("Already up to date.", self.refresh())

    def test_leftover_version_edit_on_main_is_restored_then_pulled(self):
        (self.clone / MANIFEST).write_text(
            json.dumps({"version": "0.1.0+codex.local-LOCAL"}, indent=2) + "\n", encoding="utf-8")
        self.write(str(MANIFEST), json.dumps({"version": "0.1.0+codex.local-2"}, indent=2) + "\n")
        self.publish("release 2")
        out = self.refresh()
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


if __name__ == "__main__":
    unittest.main()

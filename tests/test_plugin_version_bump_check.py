"""The pull-request check requires a Codex version change whenever plugin files change."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_plugin_version_bump.py"
MANIFEST = Path("plugins/ascent/.codex-plugin/plugin.json")


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                   cwd=cwd, check=True, capture_output=True, text=True)


class PluginVersionBumpCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "--quiet", "-b", "main")
        self.write(MANIFEST, json.dumps({"version": "0.1.0+codex.local-1"}))
        self.write("plugins/ascent/skills/example/SKILL.md", "first")
        self.write("docs/guide.md", "first")
        self.commit("base")
        git(self.repo, "checkout", "--quiet", "-b", "feature")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "--quiet", "-m", message)

    def check(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), "--base", "main"], cwd=self.repo,
                              capture_output=True, text=True)

    def test_plugin_change_without_bump_fails(self):
        self.write("plugins/ascent/skills/example/SKILL.md", "second")
        self.commit("change skill")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("still 0.1.0+codex.local-1", result.stdout)

    def test_plugin_change_with_bump_passes(self):
        self.write("plugins/ascent/skills/example/SKILL.md", "second")
        self.write(MANIFEST, json.dumps({"version": "0.1.0+codex.local-2"}))
        self.commit("change skill and bump")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("0.1.0+codex.local-1 -> 0.1.0+codex.local-2", result.stdout)

    def test_change_outside_plugin_passes_without_bump(self):
        self.write("docs/guide.md", "second")
        self.commit("docs only")
        self.assertEqual(self.check().returncode, 0)

    def test_merged_in_main_changes_do_not_count(self):
        git(self.repo, "checkout", "--quiet", "main")
        self.write("plugins/ascent/skills/example/SKILL.md", "main change")
        self.write(MANIFEST, json.dumps({"version": "0.1.0+codex.local-3"}))
        self.commit("main moves on with its own bump")
        git(self.repo, "checkout", "--quiet", "feature")
        git(self.repo, "merge", "--quiet", "--no-edit", "main")
        self.write("docs/guide.md", "second")
        self.commit("docs only on feature")
        self.assertEqual(self.check().returncode, 0)


if __name__ == "__main__":
    unittest.main()

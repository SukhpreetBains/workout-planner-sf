"""End-to-end test of the tracker engine against a scratch workspace.

Run with the project environment:
    plugins/ascent/shared/scripts/py -m unittest discover -s plugins/ascent/shared/scripts
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent

GOOD_UPDATES = """\
source_refs: ["workspace/meetings/2026-08-14 - Test.md"]
updates:
  - category: stakeholder
    action: add
    fields:
      Name: Maria Chen
      Role: VP Operations
      Influence: high
  - category: pain_point
    action: add
    fields:
      Statement: Invoice approvals take 9 days because the handoff is manual.
      Pain Type: process
      Severity: high
"""

BAD_UPDATES = """\
source_refs: ["workspace/meetings/2026-08-14 - Test.md"]
updates:
  - category: pain_point
    action: add
    fields:
      Statement: Missing required Pain Type and a bad enum below.
      Severity: enormous
"""


class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.env = {**os.environ, "EAD_REPO_ROOT": str(cls.root)}
        meetings = cls.root / "workspace" / "meetings"
        meetings.mkdir(parents=True)
        (meetings / "2026-08-14 - Test.md").write_text(
            "Maria Chen said invoice approvals take 9 days.", encoding="utf-8")
        (cls.root / "workspace" / ".system" / "proposed-updates").mkdir(parents=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_script(self, name, *args, expect=0):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / name), *args],
            capture_output=True, text=True, env=self.env, cwd=self.root)
        self.assertEqual(result.returncode, expect,
                         f"{name} {args}: {result.stdout}\n{result.stderr}")
        return result.stdout

    def test_pipeline(self):
        proposed = self.root / "workspace" / ".system" / "proposed-updates"

        out = self.run_script("sync.py", "--check-setup")
        self.assertIn("not ready", out)
        self.assertIn("trackers: 0/", out)

        out = self.run_script("init_trackers.py")
        self.assertIn("created workspace/trackers/stakeholders.xlsx", out)

        out = self.run_script("sync.py", "--check-setup")
        self.assertIn("ready: this looks like an initialized Opportunity workspace", out)

        bad = proposed / "bad.yaml"
        bad.write_text(BAD_UPDATES, encoding="utf-8")
        out = self.run_script("validate_updates.py", str(bad), expect=1)
        self.assertIn("required column 'Pain Type' is missing", out)
        self.assertIn("'Severity' must be one of", out)

        good = proposed / "good.yaml"
        good.write_text(GOOD_UPDATES, encoding="utf-8")
        self.assertIn("OK: 2 update(s) valid",
                      self.run_script("validate_updates.py", str(good)))
        out = self.run_script("apply_updates.py", str(good))
        self.assertIn("add: stakeholder STK-001", out)
        self.assertIn("add: pain_point PAIN-001", out)
        self.assertIn("synced:", out)
        self.assertFalse(good.exists(), "applied file should move out of proposed-updates")

        # update action with a valid link
        upd = proposed / "upd.yaml"
        upd.write_text(
            'source_refs: ["workspace/meetings/2026-08-14 - Test.md"]\n'
            "updates:\n"
            "  - category: pain_point\n"
            "    action: update\n"
            "    id: PAIN-001\n"
            "    fields:\n"
            "      Raised By Stakeholder IDs: STK-001\n", encoding="utf-8")
        self.assertIn("update: pain_point PAIN-001",
                      self.run_script("apply_updates.py", str(upd)))

        out = self.run_script("search.py", "invoice approval")
        self.assertIn("PAIN-001", out)
        self.assertIn("2026-08-14 - Test.md", out)
        out = self.run_script("search.py", "--id", "PAIN-001")
        self.assertIn("Raised By Stakeholder IDs: STK-001", out)

        copies = self.root / "workspace" / ".system" / "tracker-copies"
        self.assertIn("Maria Chen",
                      (copies / "stakeholder.yaml").read_text(encoding="utf-8"))

        out = self.run_script("sync.py", "--status")
        self.assertIn("not yet extracted into trackers: 1", out)


if __name__ == "__main__":
    unittest.main()

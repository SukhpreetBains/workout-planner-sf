"""The proposal validator accepts links to pending proposals, as the review inbox does.

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
SOURCE = "workspace/reference/Kickoff.md"

STAKEHOLDER = f"""\
source_refs: ["{SOURCE}"]
updates:
  - category: stakeholder
    proposal_id: "stakeholder-proposal-1"
    revision: 1
    action: add
    fields:
      Name: Maria Chen
"""


def pain_point(linked: str) -> str:
    return f"""\
source_refs: ["{SOURCE}"]
updates:
  - category: pain_point
    proposal_id: "pain-proposal-1"
    revision: 1
    action: add
    fields:
      Statement: Invoice approvals take 9 days.
      Pain Type: process
      Severity: high
      Raised By Stakeholder IDs: {linked}
"""


class PendingLinkValidationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = {**os.environ, "ASCENT_OPPORTUNITY_ROOT": str(self.root)}
        (self.root / "workspace" / "reference").mkdir(parents=True)
        (self.root / SOURCE).write_text("Maria Chen: approvals take 9 days.", encoding="utf-8")
        self.proposals = self.root / "workspace" / ".system" / "proposed-updates"
        self.proposals.mkdir(parents=True)
        self.run_script("init_trackers.py")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, name, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / name), *args], capture_output=True,
                              text=True, env=self.env, cwd=self.root)

    def validate(self, name: str, content: str) -> subprocess.CompletedProcess:
        (self.proposals / name).write_text(content, encoding="utf-8")
        return self.run_script("validate_updates.py", f"workspace/.system/proposed-updates/{name}")

    def test_links_to_a_proposal_in_the_same_file(self):
        result = self.validate("batch.yaml", STAKEHOLDER + pain_point("stakeholder-proposal-1").split("updates:\n", 1)[1])
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_links_to_a_proposal_from_an_earlier_batch(self):
        (self.proposals / "batch-1.yaml").write_text(STAKEHOLDER, encoding="utf-8")
        result = self.validate("batch-2.yaml", pain_point("stakeholder-proposal-1"))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_unknown_link_is_still_rejected(self):
        result = self.validate("batch.yaml", pain_point("no-such-proposal"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("'no-such-proposal' which is not an existing stakeholder ID", result.stdout)


if __name__ == "__main__":
    unittest.main()

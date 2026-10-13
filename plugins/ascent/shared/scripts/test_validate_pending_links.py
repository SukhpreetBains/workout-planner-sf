"""The proposal validator accepts relationships to pending proposals, as the review inbox does.

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

PERSON = f"""\
source_refs: ["{SOURCE}"]
updates:
  - category: person
    proposal_id: "person-proposal-1"
    revision: 1
    action: add
    fields:
      Name: Maria Chen
"""


def pain_point(relationships: str) -> str:
    return f"""\
source_refs: ["{SOURCE}"]
updates:
  - category: pain_point
    proposal_id: "pain-proposal-1"
    revision: 1
    action: add
    fields:
      Name: Slow invoice approvals
      Description: Invoice approvals take 9 days.
      Relationships: "{relationships}"
"""


class PendingLinkValidationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = {**os.environ, "ASCENT_PROJECT_ROOT": str(self.root)}
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
        result = self.validate("batch.yaml", PERSON + pain_point("raised_by: person-proposal-1").split("updates:\n", 1)[1])
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_links_to_a_proposal_from_an_earlier_batch(self):
        (self.proposals / "batch-1.yaml").write_text(PERSON, encoding="utf-8")
        result = self.validate("batch-2.yaml", pain_point("raised_by: person-proposal-1"))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_unknown_target_is_still_rejected(self):
        result = self.validate("batch.yaml", pain_point("raised_by: no-such-proposal"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("'no-such-proposal' which is not an existing row ID or pending proposal", result.stdout)

    def test_unknown_or_missing_meaning_is_rejected(self):
        (self.proposals / "batch-1.yaml").write_text(PERSON, encoding="utf-8")
        for value in ("caused_by: person-proposal-1", "person-proposal-1"):
            with self.subTest(value=value):
                result = self.validate("batch-2.yaml", pain_point(value))
                self.assertEqual(result.returncode, 1)
                self.assertIn("needs a meaning from", result.stdout)

    def test_self_relationship_is_rejected(self):
        result = self.validate("batch.yaml", pain_point("related_to: pain-proposal-1"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot relate an item to itself", result.stdout)


if __name__ == "__main__":
    unittest.main()

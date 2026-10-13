"""Tests for workspace-add's three-document inbox batch selection.

Run with the project environment:
    plugins/ascent/shared/scripts/py -m unittest discover -s plugins/ascent/shared/scripts
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "select_inbox_batch.py"


class SelectInboxBatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inbox = self.root / "workspace" / "inbox"
        self.inbox.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name: str, mtime: int) -> None:
        path = self.inbox / name
        path.write_text(name, encoding="utf-8")
        os.utime(path, (mtime, mtime))

    def select(self) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=True,
            env={**os.environ, "ASCENT_PROJECT_ROOT": str(self.root)}, cwd=self.root)
        return json.loads(result.stdout)

    def names(self, batch: dict) -> list[str]:
        return [Path(item["path"]).name for item in batch["selected"]]

    def test_empty_or_missing_inbox_selects_nothing(self):
        self.assertEqual(self.select()["selected"], [])
        self.inbox.rmdir()
        batch = self.select()
        self.assertEqual((batch["selected"], batch["remaining"]), ([], 0))

    def test_selects_three_oldest_and_leaves_rest(self):
        for index, name in enumerate(["e.txt", "d.txt", "c.txt", "b.txt", "a.txt"]):
            self.add(name, 1_000 + index)
        batch = self.select()
        self.assertEqual(batch["batch_size"], 3)
        self.assertEqual(self.names(batch), ["e.txt", "d.txt", "c.txt"])
        self.assertEqual(batch["remaining"], 2)
        self.assertTrue((self.inbox / "a.txt").exists())

    def test_filename_breaks_modification_time_ties(self):
        for name in ["zeta.txt", "alpha.txt", "mid.txt", "beta.txt"]:
            self.add(name, 5_000)
        self.assertEqual(self.names(self.select()), ["alpha.txt", "beta.txt", "mid.txt"])

    def test_converted_copies_do_not_count_as_sources(self):
        self.add("Report.pdf", 100)
        self.add("Report.md", 900)
        self.add("Deck.pptx", 200)
        self.add("Deck.md", 901)
        self.add("notes.md", 300)
        self.add("later.txt", 400)
        batch = self.select()
        self.assertEqual(self.names(batch), ["Report.pdf", "Deck.pptx", "notes.md"])
        self.assertEqual(batch["remaining"], 1)
        copies = {Path(i["path"]).name: i["converted_copy"] for i in batch["selected"]}
        self.assertEqual(copies["Report.pdf"], "workspace/inbox/Report.md")
        self.assertEqual(copies["Deck.pptx"], "workspace/inbox/Deck.md")
        self.assertIsNone(copies["notes.md"])

    def test_hidden_files_are_ignored(self):
        self.add(".DS_Store", 1)
        self.add("only.txt", 2)
        batch = self.select()
        self.assertEqual((self.names(batch), batch["remaining"]), (["only.txt"], 0))


if __name__ == "__main__":
    unittest.main()

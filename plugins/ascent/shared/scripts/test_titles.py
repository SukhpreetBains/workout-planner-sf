"""Title fields are required, written summaries rather than copies of the statement.

Run with the project environment:
    plugins/ascent/shared/scripts/py -m unittest discover -s plugins/ascent/shared/scripts
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

STATEMENT = "Relying on Danielle as the only Experian routing point could slow decisions."


class TitleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ASCENT_OPPORTUNITY_ROOT"] = self.tmp.name
        for name in ("paths", "trackers", "validate_updates"):
            sys.modules.pop(name, None)
        self.paths = importlib.import_module("paths")
        self.validation = importlib.import_module("validate_updates")
        importlib.import_module("trackers").init_trackers()
        source = Path(self.tmp.name) / "workspace" / "meetings" / "2026-08-12 - Alignment.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(STATEMENT + "\n", encoding="utf-8")
        self.schema = self.paths.load_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def problems(self, fields: dict, action: str = "add") -> list[str]:
        update = {"category": "risk", "action": action, "fields": fields}
        if action == "update":
            update["id"] = "RISK-001"
        return self.validation.validate(
            {"source_refs": ["workspace/meetings/2026-08-12 - Alignment.md"], "updates": [update]}, self.schema)

    def test_five_title_columns_are_required(self):
        required = {c["name"] for cat in self.schema["categories"].values()
                    for c in cat["columns"] if c["name"].endswith(" Title") and c.get("required")}
        self.assertEqual(required, {"Risk Title", "Assumption Title", "Issue Title",
                                    "Decision Title", "Dependency Title"})

    def test_short_summary_title_passes(self):
        self.assertEqual(self.problems({"Statement": STATEMENT, "Risk Title": "Single-point routing through Danielle"}), [])

    def test_missing_title_is_rejected_not_invented(self):
        fields = {"Statement": STATEMENT}
        self.assertIn("required column 'Risk Title' is missing", " ".join(self.problems(fields)))
        self.assertNotIn("Risk Title", fields)

    def test_title_repeating_the_statement_is_rejected(self):
        self.assertIn("repeats the statement", " ".join(self.problems({"Statement": STATEMENT, "Risk Title": STATEMENT})))

    def test_cut_off_title_is_rejected(self):
        for cut in ("Relying on Danielle as the only Experian…", "Relying on Danielle as the only Experian..."):
            self.assertIn("looks cut off", " ".join(self.problems({"Statement": STATEMENT, "Risk Title": cut})))

    def test_updates_to_existing_rows_do_not_need_a_title(self):
        problems = " ".join(self.problems({"Status": "open"}, action="update"))
        self.assertNotIn("Risk Title", problems)


if __name__ == "__main__":
    unittest.main()

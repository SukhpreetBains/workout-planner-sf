"""Names are required, written summaries rather than copies of the description.

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

DESCRIPTION = "Relying on Danielle as the only Experian routing point could slow decisions."


class NameTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ASCENT_PROJECT_ROOT"] = self.tmp.name
        for name in ("paths", "trackers", "validate_updates"):
            sys.modules.pop(name, None)
        self.paths = importlib.import_module("paths")
        self.validation = importlib.import_module("validate_updates")
        importlib.import_module("trackers").init_trackers()
        source = Path(self.tmp.name) / "workspace" / "meetings" / "2026-08-12 - Alignment.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(DESCRIPTION + "\n", encoding="utf-8")
        self.schema = self.paths.load_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def problems(self, fields: dict, action: str = "add") -> list[str]:
        update = {"category": "risk", "action": action, "fields": fields}
        if action == "update":
            update["id"] = "RSK-001"
        return self.validation.validate(
            {"source_refs": ["workspace/meetings/2026-08-12 - Alignment.md"], "updates": [update]}, self.schema)

    def test_every_category_requires_a_name_and_signals_a_description(self):
        for key, category in self.schema["categories"].items():
            required = {c["name"] for c in category["columns"] if c.get("required")}
            with self.subTest(category=key):
                self.assertIn("Name", required)
                self.assertEqual("Description" in required, category["group"] == "signal")

    def test_short_summary_name_passes(self):
        self.assertEqual(self.problems({"Description": DESCRIPTION, "Name": "Single-point routing through Danielle"}), [])

    def test_missing_name_is_rejected_not_invented(self):
        fields = {"Description": DESCRIPTION}
        self.assertIn("required column 'Name' is missing", " ".join(self.problems(fields)))
        self.assertNotIn("Name", fields)

    def test_name_repeating_the_description_is_rejected(self):
        self.assertIn("repeats the description", " ".join(self.problems({"Description": DESCRIPTION, "Name": DESCRIPTION})))

    def test_cut_off_name_is_rejected(self):
        for cut in ("Relying on Danielle as the only Experian…", "Relying on Danielle as the only Experian..."):
            self.assertIn("looks cut off", " ".join(self.problems({"Description": DESCRIPTION, "Name": cut})))

    def test_updates_to_existing_rows_do_not_need_a_name(self):
        problems = " ".join(self.problems({"Status": "active"}, action="update"))
        self.assertNotIn("'Name'", problems)


if __name__ == "__main__":
    unittest.main()

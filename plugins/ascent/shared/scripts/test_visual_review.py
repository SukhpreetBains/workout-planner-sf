"""Acceptance coverage for the visual review inbox and RAIDD migration."""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import yaml
from openpyxl import Workbook, load_workbook


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class VisualReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["EAD_REPO_ROOT"] = str(self.root)
        for name in ("paths", "trackers", "validate_updates", "review_store", "review_server", "sync"):
            sys.modules.pop(name, None)
        self.paths = importlib.import_module("paths")
        self.trackers = importlib.import_module("trackers")
        self.validation = importlib.import_module("validate_updates")
        self.store = importlib.import_module("review_store")
        self.server_module = importlib.import_module("review_server")
        self.trackers.init_trackers()
        meeting = self.root / "workspace" / "meetings" / "2026-08-27 - Review.md"
        meeting.parent.mkdir(parents=True, exist_ok=True)
        meeting.write_text("The release may slip if test data arrives late.\n", encoding="utf-8")
        self.paths.PROPOSED_UPDATES_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def proposal(self, updates: list[dict], name: str = "review.yaml") -> Path:
        path = self.paths.PROPOSED_UPDATES_DIR / name
        path.write_text(yaml.safe_dump({
            "source_refs": ["workspace/meetings/2026-08-27 - Review.md"],
            "updates": updates,
        }, sort_keys=False), encoding="utf-8")
        return path

    def risk(self, **overrides) -> dict:
        value = {
            "category": "risk",
            "action": "add",
            "fields": {
                "Statement": "Test data may arrive late.",
                "Probability": 0.9,
                "Impact": "Very High",
                "Status": "Active",
            },
            "evidence": [{
                "source_ref": "workspace/meetings/2026-08-27 - Review.md",
                "excerpt": "The release may slip if test data arrives late.",
                "line_start": 1,
            }],
        }
        value.update(overrides)
        return value

    def test_legacy_proposals_upgrade_with_stable_identity(self):
        path = self.proposal([self.risk()])
        first = self.store.list_cards()["cards"][0]
        second = self.store.list_cards()["cards"][0]
        self.assertEqual(first["proposal_id"], second["proposal_id"])
        self.assertEqual(first["revision"], 1)
        stored = yaml.safe_load(path.read_text(encoding="utf-8"))["updates"][0]
        self.assertEqual(stored["proposal_id"], first["proposal_id"])
        self.assertIn("review", stored)

    def test_typed_validation_and_path_containment(self):
        update = self.risk(fields={"Statement": "Risk", "Probability": 1.2,
                                           "Impact": "Very High", "Date Raised": "not-a-date"})
        document = {"source_refs": ["../outside.md"], "updates": [update]}
        problems = self.validation.validate(document, self.paths.load_schema())
        self.assertTrue(any("at most 0.9" in problem for problem in problems))
        self.assertTrue(any("ISO date" in problem for problem in problems))
        self.assertTrue(any("escapes the workspace root" in problem for problem in problems))

    def test_risk_formula_and_existing_blank_values(self):
        schema = self.paths.load_schema()
        row_id = self.trackers.upsert_row("risk", self.risk()["fields"] | {
            "Source Refs": "workspace/meetings/2026-08-27 - Review.md"
        }, schema)
        row = next(row for row in self.trackers.read_rows("risk", schema)
                   if row["Risk ID"] == row_id)
        self.assertEqual(row["Calculated Severity"], "Sev 1")
        self.assertAlmostEqual(float(row["Risk Score"]), 0.72)

        path = self.root / "workspace" / "trackers" / "raid.xlsx"
        workbook = load_workbook(path)
        sheet = workbook["Risks"]
        sheet.append(["RSK-099", "Legacy risk"])
        workbook.save(path)
        self.trackers.init_trackers(schema)
        legacy = next(row for row in self.trackers.read_rows("risk", schema)
                      if row["Risk ID"] == "RSK-099")
        self.assertEqual(legacy["Calculated Severity"], "")
        self.assertEqual(legacy["Risk Score"], "")

    def test_migration_preserves_rows_formulas_and_custom_columns(self):
        path = self.root / "workspace" / "trackers" / "raid.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Risks"
        sheet.append(["Risk ID", "Statement", "Custom Score", "Source Refs", "Notes",
                      "Created At", "Updated At"])
        sheet.append(["RSK-004", "Existing", "=LEN(B2)", "source.md", "Keep me", "", ""])
        workbook.save(path)
        self.trackers.init_trackers()
        migrated = load_workbook(path, data_only=False)
        sheet = migrated["Risks"]
        headers = [cell.value for cell in sheet[1]]
        self.assertIn("Issue Title", [cell.value for cell in migrated["Issues"][1]])
        self.assertIn("Delivery Date", [cell.value for cell in migrated["Dependencies"][1]])
        self.assertEqual(sheet.cell(2, headers.index("Custom Score") + 1).value, "=LEN(B2)")
        self.assertEqual(sheet.cell(2, headers.index("Notes") + 1).value, "Keep me")

    def test_autosave_conflict_and_audit(self):
        self.proposal([self.risk()])
        card = next(card for card in self.store.list_cards()["cards"]
                    if card["category"] == "risk")
        fields = dict(card["fields"], Owner="Sam")
        saved = self.store.autosave(card["proposal_id"], card["revision"], fields)
        self.assertEqual(saved["revision"], 2)
        with self.assertRaises(self.store.RevisionConflict):
            self.store.autosave(card["proposal_id"], 1, fields)
        history = self.paths.REVIEW_HISTORY.read_text(encoding="utf-8")
        self.assertIn('"event": "edit"', history)

    def test_accept_is_item_level_atomic_and_idempotent(self):
        self.proposal([self.risk(), {
            "category": "issue", "action": "add",
            "fields": {"Statement": "UAT is delayed", "Status": "active"},
        }])
        card = next(card for card in self.store.list_cards()["cards"]
                    if card["category"] == "risk")
        result = self.store.accept(card["proposal_id"], card["revision"], "accept-one")
        duplicate = self.store.accept(card["proposal_id"], card["revision"], "accept-one")
        self.assertEqual(result, duplicate)
        self.assertEqual(len(self.store.list_cards()["cards"]), 1)
        rows = self.trackers.read_rows("risk", self.paths.load_schema())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Calculated Severity"], "Sev 1")
        self.assertTrue(any(self.paths.APPLIED_UPDATES_DIR.glob("*.yaml")))

    def test_accept_rolls_back_when_sync_fails(self):
        self.proposal([self.risk()])
        card = self.store.list_cards()["cards"][0]
        failed = __import__("subprocess").CompletedProcess([], 1, stdout="", stderr="sync failed")
        with mock.patch.object(self.store.subprocess, "run", return_value=failed):
            with self.assertRaises(self.store.ReviewError):
                self.store.accept(card["proposal_id"], card["revision"], "rollback")
        self.assertEqual(self.trackers.read_rows("risk", self.paths.load_schema()), [])
        self.assertEqual(len(self.store.list_cards()["cards"]), 1)

    def test_cross_category_raidd_links(self):
        schema = self.paths.load_schema()
        issue_id = self.trackers.upsert_row("issue", {
            "Statement": "UAT is delayed", "Status": "active",
            "Source Refs": "workspace/meetings/2026-08-27 - Review.md",
        }, schema)
        update = {
            "category": "decision", "action": "add",
            "fields": {"Statement": "Add test capacity", "Status": "decided",
                       "Linked RAIDD IDs": issue_id},
        }
        problems = self.validation.validate({
            "source_refs": ["workspace/meetings/2026-08-27 - Review.md"],
            "updates": [update],
        }, schema)
        self.assertEqual(problems, [])

    def test_reject_never_writes_and_flag_stays_pending(self):
        self.proposal([self.risk(), self.risk(fields={"Statement": "Second risk"})])
        first, second = self.store.list_cards()["cards"]
        self.store.reject(first["proposal_id"], first["revision"], "Duplicate")
        self.assertEqual(self.trackers.read_rows("risk", self.paths.load_schema()), [])
        flagged = self.store.flag(second["proposal_id"], second["revision"], "Confirm impact")
        self.assertEqual(flagged["sequence"], 1)
        remaining = self.store.list_cards()["cards"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["review"]["state"], "flagged")
        self.assertEqual(self.store.queue_after(0)["items"][0]["note"], "Confirm impact")

    def test_concurrent_revision_allows_only_one_edit(self):
        self.proposal([self.risk()])
        card = self.store.list_cards()["cards"][0]
        outcomes = []

        def edit(owner: str):
            try:
                outcomes.append(self.store.autosave(card["proposal_id"], 1,
                                                     dict(card["fields"], Owner=owner)))
            except self.store.RevisionConflict:
                outcomes.append("conflict")

        threads = [threading.Thread(target=edit, args=(owner,)) for owner in ("A", "B")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(outcome == "conflict" for outcome in outcomes), 1)

    def test_http_security_and_event_waiting(self):
        self.proposal([self.risk()])
        server = self.server_module.ReviewServer(("127.0.0.1", 0), "secret", self.root, "test")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        self.assertEqual(server.server_address[0], "127.0.0.1")
        self.assertTrue(json.load(urllib.request.urlopen(f"{base}/api/health"))["ok"])

        request = urllib.request.Request(f"{base}/api/autosave", data=b"{}", method="POST",
                                         headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(request)
        self.assertEqual(denied.exception.code, 403)

        malformed = urllib.request.Request(f"{base}/api/autosave", data=b"not-json", method="POST",
            headers={"Content-Type": "application/json", "X-Review-Token": "secret"})
        with self.assertRaises(urllib.error.HTTPError) as bad:
            urllib.request.urlopen(malformed)
        self.assertEqual(bad.exception.code, 400)

        unsupported = urllib.request.Request(f"{base}/api/inbox", data=b"{}", method="PUT")
        with self.assertRaises(urllib.error.HTTPError) as method:
            urllib.request.urlopen(unsupported)
        self.assertEqual(method.exception.code, 405)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    def test_start_reuses_server_and_recovers_stale_state(self):
        stale = self.root / "workspace" / ".system" / "review-server.json"
        stale.write_text(json.dumps({
            "pid": 999999, "port": 9, "token": "stale", "instance_id": "stale"
        }), encoding="utf-8")
        self.assertEqual(self.server_module.start(self.root), 0)
        first = self.server_module.read_state(self.root)
        try:
            self.assertTrue(self.server_module.healthy(first))
            self.assertEqual(self.server_module.start(self.root), 0)
            second = self.server_module.read_state(self.root)
            self.assertEqual(first["port"], second["port"])
        finally:
            self.server_module.stop(self.root)


if __name__ == "__main__":
    unittest.main()

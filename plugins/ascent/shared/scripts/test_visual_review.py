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
        os.environ["ASCENT_OPPORTUNITY_ROOT"] = str(self.root)
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
                "Risk Title": "Late test data",
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

    def test_trackers_only_sync_exports_accepted_values_without_document_scan(self):
        self.proposal([self.risk(), self.risk(fields={"Risk Title": "Pending risk", "Statement": "Still pending."})])
        card = self.store.list_cards()["cards"][0]
        self.store.accept(card["proposal_id"], card["revision"], "snapshot-accept")
        sync_module = importlib.import_module("sync")
        index_before = self.paths.SEARCH_DB.read_bytes()
        state_before = self.paths.SYNC_STATE.read_bytes()
        copy_path = self.paths.TRACKER_COPIES_DIR / "risk.yaml"
        copy_path.unlink()
        with mock.patch.object(sys, "argv", ["sync.py", "--trackers-only"]), \
                mock.patch.object(sync_module, "workspace_files", side_effect=AssertionError("document scan")), \
                mock.patch.object(sync_module, "build_search_index", side_effect=AssertionError("index rebuild")):
            self.assertEqual(sync_module.main(), 0)
        snapshot = yaml.safe_load(copy_path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["count"], 1)
        self.assertEqual(snapshot["rows"][0]["Statement"], card["fields"]["Statement"])
        self.assertTrue(snapshot["rows"][0]["Risk ID"])
        self.assertIn("Source Refs", snapshot["rows"][0])
        self.assertEqual(self.paths.SEARCH_DB.read_bytes(), index_before)
        self.assertEqual(self.paths.SYNC_STATE.read_bytes(), state_before)
        self.assertEqual(len(self.store.list_cards()["cards"]), 1)

    def test_legacy_proposals_upgrade_with_stable_identity(self):
        path = self.proposal([self.risk()])
        first = self.store.list_cards()["cards"][0]
        second = self.store.list_cards()["cards"][0]
        self.assertEqual(first["proposal_id"], second["proposal_id"])
        self.assertEqual(first["revision"], 1)
        stored = yaml.safe_load(path.read_text(encoding="utf-8"))["updates"][0]
        self.assertEqual(stored["proposal_id"], first["proposal_id"])
        self.assertIn("review", stored)

    def test_manual_proposal_is_pending_and_categories_include_empty_tabs(self):
        created = self.store.create("decision", "User Submitted")
        inbox = self.store.list_cards()
        card = next(card for card in inbox["cards"] if card["proposal_id"] == created["proposal_id"])
        self.assertEqual(card["category"], "decision")
        self.assertEqual(card["review"]["state"], "pending")
        self.assertEqual(card["source_refs"], ["User Submitted"])
        self.assertIn("risk", [category["id"] for category in inbox["categories"]])
        self.assertEqual(inbox["counts"].get("risk", 0), 0)

    def test_typed_validation_and_path_containment(self):
        update = self.risk(fields={"Risk Title": "Bad probability", "Statement": "Risk", "Probability": 1.2,
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
            "fields": {"Issue Title": "UAT delay", "Statement": "UAT is delayed", "Status": "active"},
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

    def test_accept_explains_onedrive_file_timeout_and_preserves_proposal(self):
        self.proposal([self.risk()])
        card = self.store.list_cards()["cards"][0]
        timeout = OSError(self.store.errno.ETIMEDOUT, "Operation timed out")
        with mock.patch.object(self.store, "upsert_row", side_effect=timeout):
            with self.assertRaisesRegex(self.store.ReviewError, "OneDrive"):
                self.store.accept(card["proposal_id"], card["revision"], "onedrive-timeout")
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
            "fields": {"Decision Title": "More test capacity", "Statement": "Add test capacity", "Status": "decided",
                       "Linked RAIDD IDs": issue_id},
        }
        problems = self.validation.validate({
            "source_refs": ["workspace/meetings/2026-08-27 - Review.md"],
            "updates": [update],
        }, schema)
        self.assertEqual(problems, [])

    def test_reject_never_writes_and_flag_stays_pending(self):
        self.proposal([self.risk(), self.risk(fields={"Risk Title": "Second risk title", "Statement": "Second risk"})])
        first, second = self.store.list_cards()["cards"]
        self.store.reject(first["proposal_id"], first["revision"], "Duplicate")
        self.assertEqual(self.trackers.read_rows("risk", self.paths.load_schema()), [])
        flagged = self.store.flag(second["proposal_id"], second["revision"], "Confirm impact")
        self.assertEqual(flagged["sequence"], 1)
        remaining = self.store.list_cards()["cards"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["review"]["state"], "flagged")
        self.assertEqual(self.store.queue_after(0)["items"][0]["note"], "Confirm impact")

        progress = self.store.list_cards()["progress"]
        self.assertEqual(progress["pending"], 1)
        self.assertEqual(progress["accepted"], 0)
        self.assertEqual(progress["rejected"], 1)
        self.assertEqual(progress["flagged"], 1)
        self.assertEqual(progress["completed"], 1)
        self.assertEqual(progress["total"], 2)
        self.assertEqual(progress["categories"]["risk"]["pending"], 1)
        self.assertEqual(progress["categories"]["risk"]["rejected"], 1)

    def test_progress_summary_counts_archived_accepts_by_category(self):
        self.proposal([self.risk()])
        card = self.store.list_cards()["cards"][0]
        self.store.accept(card["proposal_id"], card["revision"], "progress-accept")

        progress = self.store.list_cards()["progress"]
        self.assertEqual(progress["pending"], 0)
        self.assertEqual(progress["accepted"], 1)
        self.assertEqual(progress["rejected"], 0)
        self.assertEqual(progress["completed"], 1)
        self.assertEqual(progress["total"], 1)
        self.assertEqual(progress["categories"]["risk"]["accepted"], 1)
        self.assertEqual(progress["categories"]["risk"]["total"], 1)

    def test_rejecting_an_accepted_value_removes_it_and_keeps_its_evidence(self):
        self.proposal([self.risk()])
        card = self.store.list_cards()["cards"][0]
        accepted = self.store.accept(card["proposal_id"], card["revision"], "accepted-rejection")
        source_refs = ["workspace/meetings/2026-08-27 - Review.md"]

        # Older accepted archives predate their explicit tracker ID link.
        applied = next(self.paths.APPLIED_UPDATES_DIR.glob("*.yaml"))
        archived = yaml.safe_load(applied.read_text(encoding="utf-8"))
        archived.pop("tracker_id")
        applied.write_text(yaml.safe_dump(archived, sort_keys=False), encoding="utf-8")

        accepted_row = self.trackers.read_rows("risk", self.paths.load_schema())[0]
        evidence = self.store.accepted_evidence("risk", accepted["tracker_id"], accepted_row, source_refs)
        self.assertEqual(evidence, card["evidence"])

        result = self.store.reject_accepted("risk", accepted["tracker_id"], "No longer relevant")
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(self.trackers.read_rows("risk", self.paths.load_schema()), [])
        rejected = list(self.paths.REJECTED_UPDATES_DIR.glob("accepted-risk-*.yaml"))
        self.assertEqual(len(rejected), 1)
        archive = yaml.safe_load(rejected[0].read_text(encoding="utf-8"))
        self.assertEqual(archive["updates"][0]["evidence"], card["evidence"])

        progress = self.store.list_cards()["progress"]
        self.assertEqual(progress["accepted"], 0)
        self.assertEqual(progress["rejected"], 1)

    def test_returning_an_accepted_value_to_pending_keeps_links_unchanged(self):
        self.proposal([self.risk()])
        card = self.store.list_cards()["cards"][0]
        accepted = self.store.accept(card["proposal_id"], card["revision"], "accepted-pending")

        with mock.patch.object(self.store, "resolve_links") as resolve_links:
            result = self.store.move_accepted_to_pending("risk", accepted["tracker_id"])

        resolve_links.assert_not_called()

        self.assertEqual(result["decision"], "pending")
        self.assertEqual(self.trackers.read_rows("risk", self.paths.load_schema()), [])
        pending = self.store.list_cards()["cards"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["proposal_id"], result["proposal_id"])
        self.assertEqual(pending[0]["fields"]["Statement"], card["fields"]["Statement"])
        self.assertEqual(pending[0]["evidence"], card["evidence"])
        self.assertEqual(self.store.list_cards()["progress"]["accepted"], 0)
        self.assertEqual(self.store.list_cards()["progress"]["pending"], 1)

    def test_applied_evidence_index_keeps_every_update_in_a_batch_archive(self):
        self.paths.APPLIED_UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        archive = self.paths.APPLIED_UPDATES_DIR / "batch.yaml"
        archive.write_text(yaml.safe_dump({"updates": [
            {"category": "risk", "fields": {"Statement": "First risk"},
             "evidence": [{"source_ref": "workspace/first.md", "excerpt": "First evidence"}]},
            {"category": "risk", "fields": {"Statement": "Second risk"},
             "evidence": [{"source_ref": "workspace/second.md", "excerpt": "Second evidence"}]},
        ]}, sort_keys=False), encoding="utf-8")

        evidence = self.store.accepted_evidence(
            "risk", "R002", {"Statement": "Second risk"}, ["workspace/second.md"],
            self.store.applied_evidence_index())
        self.assertEqual(evidence[0]["source_ref"], "workspace/second.md")

    def test_display_label_covers_non_statement_categories(self):
        schema = self.paths.load_schema()
        cases = [
            ("stakeholder", {"Name": "Executive Sponsor"}, "Executive Sponsor"),
            ("system", {"Name": "Customer Portal"}, "Customer Portal"),
            ("open_question", {"Question": "Who approves the budget?"}, "Who approves the budget?"),
            ("session", {"Name": "Kickoff workshop"}, "Kickoff workshop"),
            ("operating_model", {"Name": "Delivery governance"}, "Delivery governance"),
            ("plan_item", {"Name": "Confirm ownership"}, "Confirm ownership"),
            ("workflow_stage", {"Workflow Name": "Intake", "Stage Name": "Assess"}, "Intake: Assess"),
        ]
        for category, fields, expected in cases:
            with self.subTest(category=category):
                self.assertEqual(self.store.display_label(category, fields, schema), expected)

        self.assertEqual(self.store.display_label("session", {"Session ID": "SES-001"}, schema), "SES-001")

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

    def test_permission_denied_health_preserves_state(self):
        state = {"pid": 123, "port": 456, "token": "test", "instance_id": "existing"}
        self.server_module.write_state(self.root, state)
        denied = urllib.error.URLError(PermissionError(1, "Operation not permitted"))
        for operation in (self.server_module.start, self.server_module.status,
                          self.server_module.stop):
            with self.subTest(operation=operation.__name__), \
                    mock.patch.object(self.server_module, "request_json", side_effect=denied), \
                    mock.patch.object(self.server_module.subprocess, "Popen") as spawn:
                with self.assertRaises(self.server_module.LocalServerPermissionError):
                    operation(self.root)
                spawn.assert_not_called()
                self.assertEqual(self.server_module.read_state(self.root), state)

    def test_bind_permission_denied_has_actionable_exit(self):
        with mock.patch.object(self.server_module, "ReviewServer", side_effect=PermissionError(1, "denied")):
            self.assertEqual(self.server_module.serve(self.root, "test", "test"), 77)
        self.assertIsNone(self.server_module.read_state(self.root))

    def test_failed_child_exits_without_startup_timeout(self):
        for code in (77, 1):
            child = mock.Mock()
            child.poll.return_value = code
            with self.subTest(code=code), \
                    mock.patch.object(self.server_module.subprocess, "Popen", return_value=child), \
                    mock.patch.object(self.server_module.time, "sleep") as sleep:
                self.assertEqual(self.server_module.start(self.root), code)
                sleep.assert_not_called()
                self.assertFalse(self.server_module.STARTED_PROCESSES)

    def test_start_passes_dash_prefixed_token_as_one_argument(self):
        child = mock.Mock()
        child.poll.return_value = 1
        with mock.patch.object(self.server_module.secrets, "token_urlsafe", return_value="-demo-token"), \
                mock.patch.object(self.server_module.subprocess, "Popen", return_value=child) as spawn:
            self.assertEqual(self.server_module.start(self.root), 1)
        self.assertIn("--token=-demo-token", spawn.call_args.args[0])

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

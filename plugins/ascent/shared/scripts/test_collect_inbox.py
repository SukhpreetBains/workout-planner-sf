"""Tests for workspace-collect's plan, write, fail, and schedule commands.

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

import yaml

SCRIPTS = Path(__file__).resolve().parent
SCRIPT = SCRIPTS / "collect_inbox.py"

RECORD = {
    "schema_version": 1,
    "account": "Acme",
    "project": "Transformation",
    "last_verified": "2026-10-19",
    "sharepoint_locations": [],
    "messaging_platforms": [
        {
            "name": "Slack",
            "connection_state": "usable",
            "locations": [
                {"id": "slack-pod", "name": "#pod", "locator": "slack://T1/C1", "identifiers": {"channel_id": "C1"},
                 "location_type": "channel", "collect": True, "access": {"state": "available", "reason": "ok"}},
                {"id": "slack-off", "name": "#off", "locator": "slack://T1/C2", "collect": True, "enabled": False},
                {"id": "slack-uncollected", "name": "#other", "locator": "slack://T1/C3"},
            ],
        },
        {
            "name": "Microsoft Teams",
            "connection_state": "usable",
            "locations": [
                {"id": "teams-standup", "name": "Daily Standup",
                 "locator": "https://teams.microsoft.com/meet/123?p=SECRET",
                 "identifiers": {"online_meeting_id": "M1"}, "location_type": "meeting_series", "collect": True,
                 "access": {"state": "available", "reason": "ok"}},
            ],
        },
    ],
    "project_sources": [
        {"id": "jira-story", "kind": "other", "name": "SGAF-1", "locator": "https://example/SGAF-1", "collect": True},
    ],
}


class CollectInboxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.system = self.root / "workspace" / ".system"
        self.inbox = self.root / "workspace" / "inbox"
        self.system.mkdir(parents=True)
        self.inbox.mkdir(parents=True)
        (self.system / "source-context.yaml").write_text(yaml.safe_dump(RECORD), encoding="utf-8")
        self.contracts = self.root / "contracts"
        self.contracts.mkdir()
        for system in ("slack", "microsoft-teams"):
            (self.contracts / f"{system}.yaml").write_text(f"system: {system}\n", encoding="utf-8")
        self.state_file = self.system / "collection-state.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, script: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(script), *args], capture_output=True, text=True, check=check,
            env={**os.environ, "ASCENT_PROJECT_ROOT": str(self.root)}, cwd=self.root)

    def invoke(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return self.run_script(SCRIPT, *args, check=check)

    def collect(self, *args: str) -> dict:
        return json.loads(self.run_script(SCRIPT, *args).stdout)

    def set_cursor(self, source_id: str, cursor: str) -> None:
        state = yaml.safe_load(self.state_file.read_text()) if self.state_file.exists() else {}
        state.setdefault("sources", {}).setdefault(source_id, {})["cursor"] = cursor
        self.state_file.write_text(yaml.safe_dump(state), encoding="utf-8")

    def write(self, payload: dict) -> dict:
        path = self.root / "payload.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return self.collect("write", "--input", str(path))

    def front(self, relative: str) -> dict:
        text = (self.root / relative).read_text(encoding="utf-8")
        return yaml.safe_load(text.split("---")[1])

    def slack_payload(self) -> dict:
        return {
            "source_id": "slack-pod",
            "documents": [{
                "entries": [
                    {"id": "100", "at": "2026-10-19T12:00:00Z", "author": "Ann", "text": "Old parent", "context": True},
                    {"id": "101", "at": "2026-10-19T15:00:00Z", "author": "Bo", "text": "New reply", "parent": "100"},
                    {"id": "102", "at": "2026-10-19T16:00:00Z", "author": "Cy", "text": "New top-level"},
                    {"id": "099", "at": "2026-10-19T13:00:00Z", "author": "Di", "text": "Already collected"},
                ],
            }],
        }

    def test_plan_lists_only_collectable_sources(self):
        plan = self.collect("plan", "--contracts-dir", str(self.contracts))
        self.assertEqual([s["id"] for s in plan["sources"]], ["slack-pod", "teams-standup"])
        skipped = {s["id"]: s["skipped"] for s in plan["skipped"]}
        self.assertIn("disabled", skipped["slack-off"])
        self.assertIn("No collection contract", skipped["jira-story"])
        self.assertNotIn("slack-uncollected", skipped)
        self.assertEqual(plan["needs_start"], ["slack-pod", "teams-standup"])

    def test_plan_carries_contract_instructions_and_payload_format(self):
        real_contracts = SCRIPTS.parents[1] / "skills" / "workspace-collect" / "contracts"
        plan = self.collect("plan", "--contracts-dir", str(real_contracts))
        by_id = {s["id"]: s for s in plan["sources"]}
        slack = by_id["slack-pod"]["instructions"]
        self.assertEqual(slack["operations"]["read_channel"]["tool"], "slack_read_channel")
        self.assertIn("thread_lookback_days", slack["read"])
        self.assertEqual(slack["settings"]["thread_lookback_days"], 14)
        teams = by_id["teams-standup"]["instructions"]
        self.assertIn("transcript", teams["new_material"].lower())
        self.assertIn("cursor_at", plan["payload_format"])

    def test_write_reads_stdin_and_deletes_input_file(self):
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        piped = subprocess.run(
            [sys.executable, str(SCRIPT), "write", "--input", "-"], input=json.dumps(self.slack_payload()),
            capture_output=True, text=True, check=True, env={**os.environ, "ASCENT_PROJECT_ROOT": str(self.root)}, cwd=self.root)
        self.assertEqual(len(json.loads(piped.stdout)["files"]), 1)
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        path = self.system / ".collect-slack-pod.json"
        path.write_text(json.dumps(self.slack_payload()), encoding="utf-8")
        self.collect("write", "--input", str(path), "--delete-input")
        self.assertFalse(path.exists())

    def test_plan_since_starts_only_missing_cursors(self):
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        plan = self.collect("plan", "--contracts-dir", str(self.contracts), "--since", "2026-10-01T00:00:00-04:00")
        cursors = {s["id"]: s["cursor"] for s in plan["sources"]}
        self.assertEqual(cursors["slack-pod"], "2026-10-19T14:00:00Z")
        self.assertEqual(cursors["teams-standup"], "2026-10-01T04:00:00.000000Z")
        self.assertEqual(plan["needs_start"], [])
        self.assertIn("cursor_epoch", plan["sources"][0])

    def test_slack_write_keeps_new_messages_and_context_parent(self):
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        result = self.write(self.slack_payload())
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["cursor"], "2026-10-19T16:00:00.000000Z")
        text = (self.root / result["files"][0]).read_text(encoding="utf-8")
        self.assertIn("Old parent", text)
        self.assertIn("earlier message, shown for context", text)
        self.assertIn("> **Reply from Bo", text)
        self.assertIn("New top-level", text)
        self.assertNotIn("Already collected", text)
        front = self.front(result["files"][0])
        self.assertEqual(front["collected_by"], "workspace-collect")
        self.assertEqual(front["covered_from"], "2026-10-19T15:00:00.000000Z")
        self.assertEqual([p.name for p in self.inbox.iterdir() if p.name.startswith(".")], [])

    def test_rerun_with_same_payload_writes_nothing(self):
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        self.write(self.slack_payload())
        again = self.write(self.slack_payload())
        self.assertEqual(again["files"], [])
        state = yaml.safe_load(self.state_file.read_text())
        self.assertEqual(state["sources"]["slack-pod"]["last_result"]["outcome"], "nothing_new")

    def test_teams_transcript_uses_offsets_key_and_hides_passcode(self):
        self.set_cursor("teams-standup", "2026-10-18T00:00:00Z")
        payload = {
            "source_id": "teams-standup",
            "documents": [{
                "key": "T1", "title": "Daily Standup transcript", "format": "transcript",
                "started_at": "2026-10-19T14:33:44.0040879Z", "cursor_at": "2026-10-19T14:33:44.0040879Z",
                "entries": [{"offset": "00:01:06.224", "author": "Calvin", "text": "Hey."}],
            }],
        }
        result = self.write(payload)
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["cursor"], "2026-10-19T14:33:44.004087Z")
        front = self.front(result["files"][0])
        self.assertEqual(front["locator"], "https://teams.microsoft.com/meet/123")
        self.assertEqual(front["document_key"], "T1")
        text = (self.root / result["files"][0]).read_text(encoding="utf-8")
        self.assertNotIn("SECRET", text)
        self.assertIn("**Calvin:** Hey.", text)
        # Same transcript again: skipped by key even if the cursor moved back.
        self.set_cursor("teams-standup", "2026-10-18T00:00:00Z")
        self.assertEqual(self.write(payload)["files"], [])

    def test_names_never_overwrite(self):
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        first = self.write(self.slack_payload())["files"][0]
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        second = self.write(self.slack_payload())["files"][0]
        self.assertNotEqual(first, second)
        self.assertTrue(second.endswith("-2.md"))

    def test_write_refuses_unknown_source_and_missing_cursor(self):
        path = self.root / "payload.json"
        path.write_text(json.dumps({"source_id": "slack-uncollected", "documents": []}), encoding="utf-8")
        self.assertNotEqual(self.invoke("write", "--input", str(path), check=False).returncode, 0)
        path.write_text(json.dumps({"source_id": "slack-pod", "documents": []}), encoding="utf-8")
        self.assertNotEqual(self.invoke("write", "--input", str(path), check=False).returncode, 0)

    def test_bad_timestamp_writes_no_files(self):
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        payload = self.slack_payload()
        payload["documents"].append({"entries": [{"id": "x", "author": "E", "text": "no time"}]})
        path = self.root / "payload.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertNotEqual(self.invoke("write", "--input", str(path), check=False).returncode, 0)
        self.assertEqual([p for p in self.inbox.iterdir()], [])

    def test_fail_keeps_cursor(self):
        self.set_cursor("teams-standup", "2026-10-18T00:00:00Z")
        result = self.collect("fail", "--source-id", "teams-standup", "--reason", "Needs reconnecting")
        self.assertEqual(result["cursor"], "2026-10-18T00:00:00Z")
        state = yaml.safe_load(self.state_file.read_text())
        self.assertEqual(state["sources"]["teams-standup"]["last_result"]["outcome"], "failed")

    def test_schedule_starts_missing_cursors_and_unschedule_keeps_them(self):
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        result = self.collect("schedule", "--frequency", "weekly", "--weekday", "monday", "--time", "09:00",
                              "--timezone", "America/New_York", "--host", "codex", "--task-id", "task-1")
        self.assertEqual(result["cursors_started"], ["slack-off", "teams-standup", "jira-story"])
        self.assertEqual(result["schedule"]["weekday"], "monday")
        self.assertNotEqual(self.invoke("schedule", "--frequency", "weekly", "--time", "09:00", "--timezone",
                                     "America/New_York", "--host", "codex", "--task-id", "t", check=False).returncode, 0)
        self.collect("unschedule")
        status = self.collect("status")
        self.assertIsNone(status["schedule"])
        self.assertEqual(status["sources"]["slack-pod"]["cursor"], "2026-10-19T14:00:00Z")

    def test_status_and_selector_report_collected_files(self):
        self.set_cursor("slack-pod", "2026-10-19T14:00:00Z")
        written = self.write(self.slack_payload())["files"][0]
        (self.inbox / "notes.txt").write_text("dropped by the user", encoding="utf-8")
        status = self.collect("status")
        self.assertEqual([item["path"] for item in status["collected_in_inbox"]], [written])
        batch = json.loads(self.run_script(SCRIPTS / "select_inbox_batch.py").stdout)
        self.assertEqual(len(batch["selected"]), 2)
        self.assertEqual(batch["collected"], [{"path": written, "source": "Slack #pod"}])


if __name__ == "__main__":
    unittest.main()

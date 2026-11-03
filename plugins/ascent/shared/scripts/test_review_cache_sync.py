"""Focused tests for manual review of local and cloud sync versions."""

from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path
from unittest import mock
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_cache


class ReviewCacheSyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "project"
        self.relative = "workspace/trackers/example.txt"
        self.cloud = self.root / self.relative
        self.cloud.parent.mkdir(parents=True)
        self.cloud.write_text("base", encoding="utf-8")
        patcher = mock.patch.object(review_cache, "cache_dir", return_value=base / "cache")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cache = review_cache.ReviewCache(self.root)
        self.cache.prepare()
        self.local = self.cache.local_root / self.relative
        self.assertEqual(self.local.stat().st_mtime_ns, self.cloud.stat().st_mtime_ns)

    def test_recovery_backups_are_not_copied(self):
        backup = self.root / "workspace/.system/backups/snapshot/raid.xlsx"
        backup.parent.mkdir(parents=True)
        backup.write_text("old", encoding="utf-8")
        self.assertNotIn("workspace/.system/backups/snapshot/raid.xlsx", review_cache.files(self.root))
        self.assertIn(self.relative, review_cache.files(self.root))

    def test_compare_and_overwrite_one_conflicting_file(self):
        self.local.write_text("local revision", encoding="utf-8")
        self.cloud.write_text("cloud revision", encoding="utf-8")
        preview = self.cache.sync_preview()["items"]
        self.assertEqual(len(preview), 1)
        item = preview[0]
        self.assertTrue(item["local_changed"])
        self.assertTrue(item["cloud_changed"])
        self.assertEqual(item["local"]["modified_by"], "Unknown")
        self.assertIsNotNone(item["cloud"]["modified_at"])

        self.cache.overwrite_all(preview)
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "local revision")
        self.assertEqual(self.cache.sync_preview()["items"], [])
        self.assertEqual(self.cache.baseline[self.relative], review_cache.digest(self.cloud))

    def test_rejects_stale_cloud_version(self):
        self.local.write_text("local revision", encoding="utf-8")
        self.cloud.write_text("cloud revision", encoding="utf-8")
        item = self.cache.sync_preview()["items"][0]
        self.cloud.write_text("newer cloud revision", encoding="utf-8")
        with self.assertRaises(review_cache.SyncConflictError):
            self.cache.overwrite_all([item])
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "newer cloud revision")

    def test_rejects_stale_local_version(self):
        self.local.write_text("local revision", encoding="utf-8")
        self.cloud.write_text("cloud revision", encoding="utf-8")
        item = self.cache.sync_preview()["items"][0]
        self.local.write_text("newer local revision", encoding="utf-8")
        with self.assertRaises(review_cache.SyncConflictError):
            self.cache.overwrite_all([item])
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "cloud revision")

    def test_matching_contents_do_not_prompt_and_paths_are_scoped(self):
        self.local.write_text("base", encoding="utf-8")
        self.assertEqual(self.cache.sync_preview()["items"], [])
        with self.assertRaises(review_cache.SyncConflictError):
            self.cache.overwrite_all([{"path": "workspace/trackers/../../secret", "local": {}, "cloud": {}}])

    def test_overwrite_all_files_and_track_signed_in_editor(self):
        second = "workspace/trackers/another.txt"
        cloud_second = self.root / second
        cloud_second.write_text("other base", encoding="utf-8")
        local_second = self.cache.local_root / second
        local_second.write_text("another local revision", encoding="utf-8")
        self.local.write_text("local revision", encoding="utf-8")
        self.cloud.write_text("newer cloud revision", encoding="utf-8")
        with mock.patch.object(review_cache, "current_editor", return_value="Alex Reviewer"):
            self.cache.mark_local_change({self.relative, second})
        preview = self.cache.sync_preview()["items"]
        self.assertEqual({item["path"] for item in preview}, {self.relative, second})
        self.assertTrue(all(item["local"]["modified_by"] == "Alex Reviewer" for item in preview))
        self.cache.overwrite_all(preview)
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "local revision")
        self.assertEqual(cloud_second.read_text(encoding="utf-8"), "another local revision")
        editors = review_cache.read_editors(self.root)
        self.assertEqual(editors[self.relative]["modified_by"], "Alex Reviewer")
        self.assertEqual(editors[second]["modified_by"], "Alex Reviewer")

    def test_stale_file_stops_entire_batch(self):
        second = "workspace/trackers/another.txt"
        cloud_second = self.root / second
        cloud_second.write_text("other base", encoding="utf-8")
        self.cache.local_root.joinpath(second).write_text("other local", encoding="utf-8")
        self.local.write_text("local revision", encoding="utf-8")
        preview = self.cache.sync_preview()["items"]
        cloud_second.write_text("changed after comparison", encoding="utf-8")
        with self.assertRaises(review_cache.SyncConflictError):
            self.cache.overwrite_all(preview)
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "base")
        self.assertEqual(cloud_second.read_text(encoding="utf-8"), "changed after comparison")

    def test_failed_publish_restores_every_cloud_copy(self):
        second = "workspace/trackers/another.txt"
        cloud_second = self.root / second
        cloud_second.write_text("other base", encoding="utf-8")
        self.cache.local_root.joinpath(second).write_text("other local", encoding="utf-8")
        self.local.write_text("local revision", encoding="utf-8")
        preview = self.cache.sync_preview()["items"]
        copy = review_cache.atomic_copy

        def fail_second_publish(source, destination):
            if destination.resolve() == self.cloud.resolve():
                raise OSError("test write failure")
            return copy(source, destination)

        with mock.patch.object(review_cache, "atomic_copy", side_effect=fail_second_publish):
            with self.assertRaises(OSError):
                self.cache.overwrite_all(preview)
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "base")
        self.assertEqual(cloud_second.read_text(encoding="utf-8"), "other base")
        self.assertEqual(review_cache.read_editors(self.root), {})

    def test_background_sync_publishes_editor_record(self):
        self.local.write_text("local revision", encoding="utf-8")
        with mock.patch.object(review_cache, "current_editor", return_value="Alex Reviewer"):
            self.cache.mark_local_change({self.relative})
        self.cache._sync_once()
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "local revision")
        self.assertEqual(review_cache.read_editors(self.root)[self.relative]["modified_by"], "Alex Reviewer")

    def test_sync_now_returns_completed_result(self):
        self.local.write_text("local revision", encoding="utf-8")
        status = self.cache.sync_now()
        self.assertEqual(status["state"], "synced")
        self.assertEqual(status["pending"], 0)
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "local revision")

    def test_sync_now_reports_conflict_without_overwriting(self):
        self.local.write_text("local revision", encoding="utf-8")
        self.cloud.write_text("cloud revision", encoding="utf-8")
        status = self.cache.sync_now()
        self.assertEqual(status["state"], "conflict")
        self.assertEqual(status["conflicts"], [self.relative])
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "cloud revision")

    def test_workbook_last_editor_is_read_when_available(self):
        workbook = self.root / "workspace" / "trackers" / "example.xlsx"
        with ZipFile(workbook, "w") as archive:
            archive.writestr("docProps/core.xml",
                             '<coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties">'
                             '<cp:lastModifiedBy>Alex Reviewer</cp:lastModifiedBy></coreProperties>')
        self.assertEqual(review_cache.version(workbook)["modified_by"], "Alex Reviewer")


if __name__ == "__main__":
    unittest.main()

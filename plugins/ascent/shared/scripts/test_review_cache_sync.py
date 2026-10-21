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

        self.cache.overwrite_cloud(self.relative, item["local"], item["cloud"])
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "local revision")
        self.assertEqual(self.cache.sync_preview()["items"], [])
        self.assertEqual(self.cache.baseline[self.relative], review_cache.digest(self.cloud))

    def test_rejects_stale_cloud_version(self):
        self.local.write_text("local revision", encoding="utf-8")
        self.cloud.write_text("cloud revision", encoding="utf-8")
        item = self.cache.sync_preview()["items"][0]
        self.cloud.write_text("newer cloud revision", encoding="utf-8")
        with self.assertRaises(review_cache.SyncConflictError):
            self.cache.overwrite_cloud(self.relative, item["local"], item["cloud"])
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "newer cloud revision")

    def test_rejects_stale_local_version(self):
        self.local.write_text("local revision", encoding="utf-8")
        self.cloud.write_text("cloud revision", encoding="utf-8")
        item = self.cache.sync_preview()["items"][0]
        self.local.write_text("newer local revision", encoding="utf-8")
        with self.assertRaises(review_cache.SyncConflictError):
            self.cache.overwrite_cloud(self.relative, item["local"], item["cloud"])
        self.assertEqual(self.cloud.read_text(encoding="utf-8"), "cloud revision")

    def test_matching_contents_do_not_prompt_and_paths_are_scoped(self):
        self.local.write_text("base", encoding="utf-8")
        self.assertEqual(self.cache.sync_preview()["items"], [])
        with self.assertRaises(ValueError):
            self.cache.overwrite_cloud("workspace/trackers/../../secret", {}, {})

    def test_workbook_last_editor_is_read_when_available(self):
        workbook = self.root / "workspace" / "trackers" / "example.xlsx"
        with ZipFile(workbook, "w") as archive:
            archive.writestr("docProps/core.xml",
                             '<coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties">'
                             '<cp:lastModifiedBy>Alex Reviewer</cp:lastModifiedBy></coreProperties>')
        self.assertEqual(review_cache.version(workbook)["modified_by"], "Alex Reviewer")


if __name__ == "__main__":
    unittest.main()

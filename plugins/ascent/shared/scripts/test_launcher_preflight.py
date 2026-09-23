"""Regression checks for wrong-root workspace creation."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from launcher_preflight import validate


class LauncherPreflightTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.account = Path(self.temp.name)
        self.root = self.account / "Opportunity"
        for name in ("project", "trackers", "inbox", ".system"):
            (self.root / "workspace" / name).mkdir(parents=True)
        self.script = str(Path(__file__).with_name("sync.py"))

    def test_missing_root_cannot_create_account_workspace(self):
        environment = dict(os.environ)
        environment.pop("EAD_REPO_ROOT", None)
        result = subprocess.run(["bash", str(Path(__file__).with_name("py")), self.script],
                                cwd=self.account, env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("EAD_REPO_ROOT", result.stderr)
        self.assertFalse((self.account / "workspace").exists())

    def test_explicit_account_root_is_rejected_without_writes(self):
        with mock.patch.dict(os.environ, {"EAD_REPO_ROOT": str(self.account)}):
            with self.assertRaisesRegex(ValueError, "Account root"):
                validate([self.script])
        self.assertFalse((self.account / "workspace").exists())

    def test_prepared_opportunity_supports_initial_setup(self):
        with mock.patch.dict(os.environ, {"EAD_REPO_ROOT": str(self.root)}):
            validate([self.script])
        self.assertFalse((self.root / "workspace/.system/.venv").exists())

    def test_mismatched_root_and_missing_script_are_rejected(self):
        with mock.patch.dict(os.environ, {"EAD_REPO_ROOT": str(self.root)}):
            for arguments in ([self.script, "--root", str(self.account)],
                              [self.script, "--root=" + str(self.account)],
                              ["missing.py"]):
                with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                    validate(arguments)


if __name__ == "__main__":
    unittest.main()

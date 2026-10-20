"""Regression checks for wrong-root workspace creation."""

import os
import subprocess
import sys
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
        self.root = self.account / "Project"
        for name in ("project", "trackers", "inbox", ".system"):
            (self.root / "workspace" / name).mkdir(parents=True)
        self.script = str(Path(__file__).with_name("sync.py"))

    def test_missing_root_cannot_create_account_workspace(self):
        environment = dict(os.environ)
        environment.pop("ASCENT_PROJECT_ROOT", None)
        result = subprocess.run(["bash", str(Path(__file__).with_name("py")), self.script],
                                cwd=self.account, env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("prepared Project workspace", result.stderr)
        self.assertFalse((self.account / "workspace").exists())

    def launch_with_old_python(self, cache: Path) -> subprocess.CompletedProcess:
        """Run the launcher where every python on PATH is too old."""
        fake_bin = Path(self.temp.name) / "fake-bin"
        fake_bin.mkdir(exist_ok=True)
        for name in ("python3", "python3.13", "python3.12", "python3.11", "python3.10", "python"):
            fake = fake_bin / name
            fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            fake.chmod(0o755)
        environment = {key: value for key, value in os.environ.items() if key != "ASCENT_PYTHON"}
        environment.update({"PATH": f"{fake_bin}:/usr/bin:/bin", "ASCENT_PROJECT_ROOT": str(self.root),
                            "ASCENT_CACHE_DIR": str(cache), "HOME": self.temp.name})
        return subprocess.run(["bash", str(Path(__file__).with_name("py")), self.script],
                              env=environment, capture_output=True, text=True)

    def test_old_default_python_falls_back_to_cached_environment_base(self):
        cache = Path(self.temp.name) / "cache"
        seed = cache / "venvs" / "seed"
        seed.mkdir(parents=True)
        (seed / "pyvenv.cfg").write_text(f"home = /unused\nexecutable = {sys.executable}\n", encoding="utf-8")
        result = self.launch_with_old_python(cache)
        self.assertNotIn("Python 3.10 or newer is required", result.stderr)
        # Resolution succeeded: it built this project's environment and stopped at the dependency check.
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("dependencies are not installed", result.stderr)

    def test_old_default_python_without_fallback_explains_requirement(self):
        result = self.launch_with_old_python(Path(self.temp.name) / "empty-cache")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Python 3.10 or newer is required", result.stderr)

    def test_explicit_account_root_is_rejected_without_writes(self):
        with mock.patch.dict(os.environ, {"ASCENT_PROJECT_ROOT": str(self.account)}):
            with self.assertRaisesRegex(ValueError, "Account root"):
                validate([self.script])
        self.assertFalse((self.account / "workspace").exists())

    def test_prepared_project_supports_initial_setup(self):
        with mock.patch.dict(os.environ, {"ASCENT_PROJECT_ROOT": str(self.root)}):
            validate([self.script])
        self.assertFalse((self.root / "workspace/.system/.venv").exists())

    def test_mismatched_root_and_missing_script_are_rejected(self):
        with mock.patch.dict(os.environ, {"ASCENT_PROJECT_ROOT": str(self.root)}):
            for arguments in ([self.script, "--root", str(self.account)],
                              [self.script, "--root=" + str(self.account)],
                              ["missing.py"]):
                with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                    validate(arguments)


if __name__ == "__main__":
    unittest.main()

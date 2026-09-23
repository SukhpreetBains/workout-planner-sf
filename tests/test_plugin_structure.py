from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_collection.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_collection", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PluginStructureTests(unittest.TestCase):
    def test_repository_plugin_contract(self) -> None:
        validator = load_validator()
        self.assertEqual(validator.validate_repository(), [])
        self.assertEqual(
            validator.EXPECTED_SKILLS,
            {path.parent.name for path in validator.SKILLS_ROOT.glob("*/SKILL.md")},
        )


if __name__ == "__main__":
    unittest.main()

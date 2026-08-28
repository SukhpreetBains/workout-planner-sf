#!/usr/bin/env python3
"""Exercise the unified initial setup against a temporary Opportunity."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "skills" / "initial-setup" / "scripts" / "prepare-opportunity-folder.py"
SOURCE_CONTEXT = ROOT / "skills" / "initial-setup" / "scripts" / "manage-source-context.py"


def run(*args: str) -> str:
    result = subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="initial-setup-") as temp:
        account = Path(temp) / "Synthetic Account"
        account.mkdir()
        common = (
            "--account-root", str(account),
            "--opportunity-name", "Synthetic Opportunity",
        )

        output = run(str(PREPARE), "--mode", "new", *common, "--check-only")
        assert "no folders or files were created or changed" in output
        opportunity = account / "Synthetic Opportunity"
        assert not opportunity.exists()

        run(str(PREPARE), "--mode", "new", *common)
        assert (opportunity / "workspace" / "inbox").is_dir()
        assert (opportunity / "workspace" / "trackers" / "stakeholders.xlsx").is_file()
        raid = load_workbook(opportunity / "workspace" / "trackers" / "raid.xlsx", read_only=True)
        assert "Issues" in raid.sheetnames
        assert "Dependencies" in raid.sheetnames
        raid.close()
        assert (opportunity / "Deliverables" / "Discover").is_dir()
        assert (opportunity / "AGENTS.md").is_file()
        assert not (opportunity / "Content Inbox").exists()
        assert not (opportunity / "Agent Inbox").exists()

        overview = opportunity / "workspace" / "project" / "Project Overview.md"
        overview.write_text("user-owned content\n", encoding="utf-8")
        run(str(PREPARE), "--mode", "existing", *common)
        assert overview.read_text(encoding="utf-8") == "user-owned content\n"

        run(
            str(SOURCE_CONTEXT), "init", "--root", str(opportunity),
            "--account", "Synthetic Account", "--opportunity", "Synthetic Opportunity",
        )
        source_context = opportunity / "workspace" / ".system" / "source-context.yaml"
        content = source_context.read_text(encoding="utf-8")
        assert "account: \"Synthetic Account\"" in content
        assert "opportunity: \"Synthetic Opportunity\"" in content

    print("Passed unified initial-setup acceptance fixture")


if __name__ == "__main__":
    main()

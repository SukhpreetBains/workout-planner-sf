#!/usr/bin/env python3
"""Exercise the unified initial setup against a temporary Opportunity."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "plugins" / "ascent" / "skills"
PREPARE = SKILLS_ROOT / "initial-setup" / "scripts" / "prepare-opportunity-folder.py"
SOURCE_CONTEXT = SKILLS_ROOT / "initial-setup" / "scripts" / "manage-source-context.py"
INITIAL_SETUP = SKILLS_ROOT / "initial-setup" / "SKILL.md"
WORKSPACE_SETUP = SKILLS_ROOT / "initial-setup" / "references" / "project-workspace-setup.md"
PLUGIN_OVERVIEW = ROOT / "plugins" / "ascent" / "README.md"
REPOSITORY_README = ROOT / "README.md"
WALKTHROUGH = ROOT / "docs" / "opportunity-workspace-walkthrough.md"


def run(*args: str) -> str:
    result = subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def assert_workflow_contract() -> None:
    initial_setup = INITIAL_SETUP.read_text(encoding="utf-8")
    workspace_setup = WORKSPACE_SETUP.read_text(encoding="utf-8")
    plugin_overview = PLUGIN_OVERVIEW.read_text(encoding="utf-8")
    repository_readme = REPOSITORY_README.read_text(encoding="utf-8")
    walkthrough = WALKTHROUGH.read_text(encoding="utf-8")

    identity_block = re.search(
        r"```yaml\n# workspace/\.system/project\.yaml\n(.*?)```",
        workspace_setup,
        re.DOTALL,
    )
    assert identity_block is not None
    identity_lines = [line for line in identity_block.group(1).splitlines() if line.strip()]
    assert identity_lines == [
        "account: <account name>",
        "opportunity: <opportunity name>",
    ]
    assert "preserve every other existing key and value" in workspace_setup
    assert "Preserve all existing readable content" in workspace_setup

    removed_intake = ("engagement type", "short engagement summary", "key dates", "current focus")
    for phrase in removed_intake:
        assert phrase not in initial_setup.lower()
    assert "Do not ask for engagement details, summaries, dates, focus areas" in workspace_setup

    combined_setup_contract = initial_setup + workspace_setup
    assert "Do not inspect `workspace/inbox/`" in combined_setup_contract
    assert "invoke `workspace-ingest-documents`" not in combined_setup_contract
    assert "Existing documents remain untouched" in combined_setup_contract
    assert "fresh agent chat scoped to the Opportunity" in combined_setup_contract
    assert "maximum room to inspect, organize, extract, and reason" in combined_setup_contract

    assert "[workflow overview](../../README.md)" in initial_setup
    assert "[workflow overview](../../../README.md)" in workspace_setup
    assert "[Ascent Workflow Overview](plugins/ascent/README.md)" in repository_readme
    assert "[workflow overview](../plugins/ascent/README.md)" in walkthrough

    lifecycle = (
        "**Ingest documents:**",
        "**Review proposed updates:**",
        "**Investigate or summarize governed evidence:**",
        "**Create deliverables:**",
    )
    positions = [plugin_overview.index(item) for item in lifecycle]
    assert positions == sorted(positions)

    readiness_items = (
        "Environment",
        "Storage",
        "Workspace structure",
        "Codex project status",
        "Communications",
        "Trackers",
        "Identity metadata",
        "Search index",
        "Workflow guidance",
        "Fresh-chat document next step",
    )
    for item in readiness_items:
        assert item in initial_setup
    for status_group in (
        "✅ Completed automatically",
        "🔎 Verified, user action still needed",
        "⚠️ Blocked or limited by connector/runtime",
    ):
        assert status_group in initial_setup


def main() -> None:
    assert_workflow_contract()

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

        output = run(str(PREPARE), "--mode", "new", *common)
        assert "managed by a sync client" in output
        assert "OneDrive will sync" not in output
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
        generated_overview = overview.read_text(encoding="utf-8")
        assert "**Account**" in generated_overview
        assert "**Opportunity**" in generated_overview
        for optional_detail in (
            "Engagement Type",
            "Start Date",
            "End Date",
            "Background",
            "Objectives",
            "Success Metrics",
            "Scope",
            "Systems Involved",
        ):
            assert optional_detail not in generated_overview

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

#!/usr/bin/env python3
"""Exercise the unified initial setup against a temporary Opportunity."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "plugins" / "ascent" / "skills"
PREPARE = SKILLS_ROOT / "initial-setup" / "scripts" / "prepare-opportunity-folder.py"
SOURCE_CONTEXT = SKILLS_ROOT / "initial-setup" / "scripts" / "manage-source-context.py"
SETUP_WORKSPACE = SKILLS_ROOT / "initial-setup" / "scripts" / "setup-workspace.py"
RECORD_IDENTITY = SKILLS_ROOT / "initial-setup" / "scripts" / "record-identity.py"
LAUNCHER = ROOT / "plugins" / "ascent" / "shared" / "scripts" / "py"
SYNC = ROOT / "plugins" / "ascent" / "shared" / "scripts" / "sync.py"
INITIAL_SETUP = SKILLS_ROOT / "initial-setup" / "SKILL.md"
WORKSPACE_SETUP = SKILLS_ROOT / "initial-setup" / "references" / "project-workspace-setup.md"
STORAGE_DECISIONS = SKILLS_ROOT / "initial-setup" / "references" / "storage-decision-tree.md"
SETUP_READINESS = SKILLS_ROOT / "initial-setup" / "references" / "setup-readiness.md"
PLUGIN_OVERVIEW = ROOT / "plugins" / "ascent" / "README.md"
REPOSITORY_README = ROOT / "README.md"
WALKTHROUGH = ROOT / "docs" / "opportunity-workspace-walkthrough.md"


def run(*args: str) -> str:
    result = subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def run_command(argv: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def assert_workflow_contract() -> None:
    initial_setup = INITIAL_SETUP.read_text(encoding="utf-8")
    workspace_setup = WORKSPACE_SETUP.read_text(encoding="utf-8")
    plugin_overview = PLUGIN_OVERVIEW.read_text(encoding="utf-8")
    repository_readme = REPOSITORY_README.read_text(encoding="utf-8")
    walkthrough = WALKTHROUGH.read_text(encoding="utf-8")

    assert SETUP_WORKSPACE.is_file()
    assert RECORD_IDENTITY.is_file()
    assert STORAGE_DECISIONS.is_file()
    assert SETUP_READINESS.is_file()
    assert "setup-workspace.py" in workspace_setup

    removed_intake = ("engagement type", "short engagement summary", "key dates", "current focus")
    for phrase in removed_intake:
        assert phrase not in initial_setup.lower()
    assert "Do not ask for engagement details, summaries, dates, focus areas" in workspace_setup

    combined_setup_contract = initial_setup + workspace_setup
    assert "Do not inspect `workspace/inbox/`" in combined_setup_contract
    assert "invoke `add-documents`" not in combined_setup_contract
    assert "Existing documents remain untouched" in combined_setup_contract
    assert "fresh agent chat scoped to the Opportunity" in combined_setup_contract

    assert "[workflow overview](../../README.md)" in initial_setup
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

    assert "storage-decision-tree.md" in initial_setup
    assert "setup-readiness.md" in initial_setup


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

        overview.write_text("# Project Overview\n\nuser-owned content\n", encoding="utf-8")
        run(str(PREPARE), "--mode", "existing", *common)
        assert overview.read_text(encoding="utf-8") == "# Project Overview\n\nuser-owned content\n"

        run(
            str(SOURCE_CONTEXT), "init", "--root", str(opportunity),
            "--account", "Synthetic Account", "--opportunity", "Synthetic Opportunity",
        )
        source_context = opportunity / "workspace" / ".system" / "source-context.yaml"
        content = source_context.read_text(encoding="utf-8")
        assert "account: \"Synthetic Account\"" in content
        assert "opportunity: \"Synthetic Opportunity\"" in content

        # Exercise the real launcher without allowing it to install anything.
        # The cached environment is pre-seeded from the test interpreter so the
        # fixture remains offline and deterministic.
        cache = Path(temp) / "ascent-cache"
        digest = hashlib.sha256(os.path.normcase(os.path.realpath(opportunity)).encode("utf-8")).hexdigest()[:20]
        venv = cache / "venvs" / digest
        created = subprocess.run(
            [sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert created.returncode == 0, created.stderr
        venv_python = venv / "bin" / "python"
        site_packages_result = subprocess.run(
            [str(venv_python), "-c", "import site; print(site.getsitepackages()[0])"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        site_packages = Path(site_packages_result.stdout.strip())

        # The bundled document runtime intentionally omits PyMuPDF and PyYAML.
        # setup-workspace does not use PyMuPDF, so a temporary import sentinel is
        # sufficient for the launcher's all-purpose dependency preflight. PyYAML
        # is required by setup, and macOS supplies it with the system Python.
        # Point this disposable venv at that existing package, without installing.
        (site_packages / "fitz.py").write_text("# unused launcher-preflight sentinel\n", encoding="utf-8")
        yaml_probe = subprocess.run(
            ["/usr/bin/python3", "-c", "import pathlib, yaml; print(pathlib.Path(yaml.__file__).parent.parent)"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if yaml_probe.returncode == 0:
            (site_packages / "system-yaml.pth").write_text(yaml_probe.stdout.strip() + "\n", encoding="utf-8")

        # Force tracker initialization to do observable work rather than merely
        # accepting the copies created from the workspace template.
        for tracker in (opportunity / "workspace" / "trackers").glob("*.xlsx"):
            tracker.unlink()

        project_identity = opportunity / "workspace" / ".system" / "project.yaml"
        project_identity.write_text(
            "# user-owned identity metadata\nphase: Discover\n",
            encoding="utf-8",
        )

        env = {
            **os.environ,
            "ASCENT_CACHE_DIR": str(cache),
            "ASCENT_OPPORTUNITY_ROOT": str(opportunity),
            "ASCENT_PYTHON": sys.executable,
        }
        setup = run_command(
            [
                str(LAUNCHER),
                str(SETUP_WORKSPACE),
                "--opportunity", str(opportunity),
                "--account", "Synthetic Account",
                "--opportunity-name", "Synthetic Opportunity",
            ],
            cwd=opportunity,
            env=env,
        )
        assert setup.returncode == 0, f"{setup.stdout}\n{setup.stderr}"
        assert "Setup workspace readiness: READY" in setup.stdout

        pointer = opportunity / "workspace" / ".system" / ".venv-path"
        assert pointer.read_text(encoding="utf-8").strip() == str(venv)
        assert not (opportunity / "workspace" / ".system" / ".venv").exists()
        assert all((opportunity / "workspace" / "trackers" / name).is_file() for name in (
            "current-state.xlsx", "future-state.xlsx", "raid.xlsx", "stakeholders.xlsx",
        ))
        identity = project_identity
        identity_content = identity.read_text(encoding="utf-8")
        assert "Synthetic Account" in identity_content
        assert "# user-owned identity metadata" in identity_content
        assert "phase: Discover" in identity_content
        assert "Synthetic Opportunity" in overview.read_text(encoding="utf-8")
        assert "user-owned content" in overview.read_text(encoding="utf-8")
        assert (opportunity / "workspace" / ".system" / "search" / "index.sqlite").is_file()

        before_identity_rerun = identity.read_bytes()
        before_overview_rerun = overview.read_bytes()
        identity_rerun = run_command(
            [
                str(venv_python),
                str(RECORD_IDENTITY),
                "--opportunity", str(opportunity),
                "--account", "Synthetic Account",
                "--opportunity-name", "Synthetic Opportunity",
            ],
            cwd=opportunity,
            env=env,
        )
        assert identity_rerun.returncode == 0, identity_rerun.stderr
        assert identity.read_bytes() == before_identity_rerun
        assert overview.read_bytes() == before_overview_rerun

        ready = run_command([str(venv_python), str(SYNC), "--check-setup"], cwd=opportunity, env=env)
        assert ready.returncode == 0
        assert "ready: this looks like an initialized Opportunity workspace" in ready.stdout

        identity.unlink()
        incomplete = run_command([str(venv_python), str(SYNC), "--check-setup"], cwd=opportunity, env=env)
        assert "not ready: this does not look like an initialized Opportunity workspace" in incomplete.stdout

    print("Passed unified initial-setup acceptance fixture")


if __name__ == "__main__":
    main()

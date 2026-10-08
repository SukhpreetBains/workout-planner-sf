#!/usr/bin/env python3
"""Validate the Ascent plugin, its skills, manifests, and marketplaces."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ascent"
SKILLS_ROOT = PLUGIN_ROOT / "skills"
PLUGIN_NAME = "ascent"
PLUGIN_VERSION = "0.1.0"
EXPECTED_SKILLS = {
    "analyze-org",
    "compose-deliverable",
    "create-deliverables",
    "design-skill-evals",
    "download-teams-transcripts",
    "initial-setup",
    "interview-me",
    "investigate-project",
    "update-deliverable-structure",
    "recursive-improvement",
    "utilities-ui-generation",
    "workspace-add",
    "workspace-review",
    "workspace-summarize",
}
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing JSON file: {path.relative_to(REPO_ROOT)}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.relative_to(REPO_ROOT)}: {exc}")
    return {}


def parse_frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}, [f"{path.relative_to(REPO_ROOT)}: missing frontmatter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, [f"{path.relative_to(REPO_ROOT)}: unterminated frontmatter"]
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            errors.append(f"{path.relative_to(REPO_ROOT)}: malformed frontmatter line {line!r}")
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, errors


def validate_markdown_links(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    for markdown in skill_dir.rglob("*.md"):
        if "node_modules" in markdown.parts or markdown.name.startswith("_"):
            continue
        for raw_target in LINK.findall(markdown.read_text(encoding="utf-8")):
            target = raw_target.strip()
            if target.startswith("<") and ">" in target:
                target = target[1:target.index(">")]
            else:
                target = target.split(" ", 1)[0]
            target = target.split("#", 1)[0].split("?", 1)[0]
            if (
                not target
                or "://" in target
                or target.startswith(("mailto:", "#", "/"))
                or any(marker in target for marker in ("<", ">", "{", "}", "*"))
            ):
                continue
            linked = markdown.parent / unquote(target)
            try:
                linked.resolve().relative_to(skill_dir.resolve())
            except ValueError:
                # Project-workspace links are runtime outputs, not plugin files.
                continue
            if not linked.exists():
                errors.append(
                    f"{markdown.relative_to(REPO_ROOT)}: missing local reference {target}"
                )
    return errors


def validate_skills() -> list[str]:
    errors: list[str] = []
    actual = {
        path.name for path in SKILLS_ROOT.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }
    if actual != EXPECTED_SKILLS:
        errors.append(
            "skill inventory mismatch: expected "
            f"{sorted(EXPECTED_SKILLS)}, found {sorted(actual)}"
        )
    if not (PLUGIN_ROOT / "shared").is_dir():
        errors.append("plugins/ascent/shared is missing")
    for name in sorted(actual):
        skill_file = SKILLS_ROOT / name / "SKILL.md"
        fields, frontmatter_errors = parse_frontmatter(skill_file)
        errors.extend(frontmatter_errors)
        if set(fields) != {"name", "description"}:
            errors.append(f"{name}: frontmatter fields must be exactly name and description")
        if fields.get("name") != name:
            errors.append(f"{name}: frontmatter name does not match its directory")
        if not fields.get("description"):
            errors.append(f"{name}: description is empty")
        errors.extend(validate_markdown_links(SKILLS_ROOT / name))
    return errors


def manifest_paths() -> list[Path]:
    return [
        PLUGIN_ROOT / "plugin.json",
        PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
        PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
        PLUGIN_ROOT / ".cursor-plugin" / "plugin.json",
    ]


def validate_manifests() -> list[str]:
    errors: list[str] = []
    for path in manifest_paths():
        manifest = load_json(path, errors)
        if not manifest:
            continue
        label = path.relative_to(REPO_ROOT)
        if manifest.get("name") != PLUGIN_NAME:
            errors.append(f"{label}: plugin name must be {PLUGIN_NAME}")
        version = str(manifest.get("version", ""))
        if version.split("+", 1)[0] != PLUGIN_VERSION:
            errors.append(f"{label}: base version must be {PLUGIN_VERSION}")
        if path.parent.name == ".codex-plugin" and not re.fullmatch(
            rf"{re.escape(PLUGIN_VERSION)}\+codex\.[a-z0-9-]+", version
        ):
            errors.append(f"{label}: Codex version must include one cachebuster suffix")
        if manifest.get("skills") != "./skills/":
            errors.append(f"{label}: skills must point to ./skills/")
        for unsupported in ("hooks", "apps", "mcpServers"):
            if unsupported in manifest:
                errors.append(f"{label}: unsupported component {unsupported} is present")
    codex = load_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json", errors)
    interface = codex.get("interface", {})
    if interface.get("displayName") != "Ascent":
        errors.append("Codex manifest displayName must be Ascent")
    if interface.get("category") != "Productivity":
        errors.append("Codex manifest category must be Productivity")
    if len(interface.get("defaultPrompt", [])) > 3:
        errors.append("Codex manifest may contain at most three default prompts")
    for field in ("composerIcon", "logo", "logoDark"):
        relative = interface.get(field)
        if not relative or not (PLUGIN_ROOT / relative).is_file():
            errors.append(f"Codex manifest {field} must point to a plugin asset")
    return errors


DEV_MARKETPLACE_NAME = "ascent-dev"
CODEX_POLICY = {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}


def validate_marketplace_entry(path: Path, expected_name: str, expected_source: dict | str,
                               check_codex_fields: bool) -> list[str]:
    errors: list[str] = []
    marketplace = load_json(path, errors)
    if not marketplace:
        return errors
    label = path.relative_to(REPO_ROOT)
    if marketplace.get("name") != expected_name:
        errors.append(f"{label}: marketplace name must be {expected_name}")
    plugins = marketplace.get("plugins", [])
    if len(plugins) != 1 or plugins[0].get("name") != PLUGIN_NAME:
        errors.append(f"{label}: marketplace must contain only the Ascent plugin")
        return errors
    entry = plugins[0]
    if entry.get("source") != expected_source:
        errors.append(f"{label}: plugin source must be {expected_source}")
    if check_codex_fields:
        if entry.get("policy") != CODEX_POLICY:
            errors.append(f"{label}: Codex policy fields are invalid")
        if entry.get("category") != "Productivity":
            errors.append(f"{label}: Codex category must be Productivity")
    return errors


def validate_marketplaces() -> list[str]:
    errors: list[str] = []
    for path in (
        REPO_ROOT / ".claude-plugin" / "marketplace.json",
        REPO_ROOT / ".github" / "plugin" / "marketplace.json",
        REPO_ROOT / ".cursor-plugin" / "marketplace.json",
    ):
        errors += validate_marketplace_entry(path, PLUGIN_NAME, "./plugins/ascent", check_codex_fields=False)

    # The canonical Codex marketplace is Git-sourced: this is what real end-user installs
    # discover (`codex plugin marketplace add Slalom/ascent`), re-cloned and version-checked
    # by Codex itself on every launch. It intentionally does not read this local checkout.
    errors += validate_marketplace_entry(
        REPO_ROOT / ".agents" / "plugins" / "marketplace.json",
        PLUGIN_NAME,
        {"source": "git-subdir", "url": "Slalom/ascent", "path": "plugins/ascent", "ref": "main"},
        check_codex_fields=True,
    )
    # The dev-only marketplace stays local-sourced so `refresh_codex_plugin.py` and local
    # iteration keep reading this checkout directly, uncommitted edits included.
    errors += validate_marketplace_entry(
        REPO_ROOT / ".agents" / "plugins" / "marketplace.local.json",
        DEV_MARKETPLACE_NAME,
        {"source": "local", "path": "./plugins/ascent"},
        check_codex_fields=True,
    )
    return errors


def validate_repository_shape() -> list[str]:
    errors: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        if path.is_symlink():
            errors.append(f"symlink is not allowed: {path.relative_to(REPO_ROOT)}")
    for old_path in (
        REPO_ROOT / ".agents" / "skills",
        REPO_ROOT / ".claude" / "skills",
        REPO_ROOT / ".codex" / "skills",
        REPO_ROOT / ".cursor" / "skills",
        REPO_ROOT / "skills",
    ):
        if old_path.exists() or old_path.is_symlink():
            errors.append(f"legacy skill path remains: {old_path.relative_to(REPO_ROOT)}")
    active_files = [
        *REPO_ROOT.glob("tests/*.py"),
        *REPO_ROOT.glob("evals/**/*.py"),
        REPO_ROOT / "docs" / "evals_workbench.py",
    ]
    for path in active_files:
        if not path.is_file() or path.name == "telemetry_acceptance.py":
            continue
        text = path.read_text(encoding="utf-8")
        if 'ROOT / "skills"' in text or 'REPO_ROOT / "skills"' in text:
            errors.append(f"active code uses legacy root skills path: {path.relative_to(REPO_ROOT)}")
    return errors


def validate_repository() -> list[str]:
    errors: list[str] = []
    errors.extend(validate_skills())
    errors.extend(validate_manifests())
    errors.extend(validate_marketplaces())
    errors.extend(validate_repository_shape())
    return errors


def main() -> int:
    errors = validate_repository()
    if errors:
        print("Ascent plugin validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Ascent plugin validation passed for {len(EXPECTED_SKILLS)} skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

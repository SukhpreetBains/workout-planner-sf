#!/usr/bin/env python3
"""Validate the structure and local references of the two project-context skills."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("discover-project-context", "retrieve-project-context")
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def validate_skill(name: str) -> list[str]:
    errors: list[str] = []
    skill_dir = ROOT / "skills" / name
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"{name}: missing SKILL.md"]
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or lines[0] != "---":
        return [f"{name}: missing frontmatter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return [f"{name}: unterminated frontmatter"]
    fields = {}
    for line in lines[1:end]:
        if ":" not in line:
            errors.append(f"{name}: malformed frontmatter line {line!r}")
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    if set(fields) != {"name", "description"}:
        errors.append(f"{name}: frontmatter fields must be exactly name and description")
    if fields.get("name") != name:
        errors.append(f"{name}: frontmatter name does not match directory")
    if not fields.get("description"):
        errors.append(f"{name}: description is empty")
    for target in LINK.findall("\n".join(lines[end + 1:])):
        target = target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if not (skill_dir / target).exists():
            errors.append(f"{name}: missing local reference {target}")
    return errors


def main() -> None:
    errors = [error for skill in SKILLS for error in validate_skill(skill)]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Validated structure and local references for {len(SKILLS)} skills")


if __name__ == "__main__":
    main()

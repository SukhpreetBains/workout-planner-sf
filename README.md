# Ascent Discovery AI Skill Library

This repository is the scaffold for a reusable, host-neutral Discovery AI skill library.

## Status

The 21 primary skill packages are stubs. Their `SKILL.md`, reference, and template files define intended ownership and package shape only; they do not implement workflows.

## Architecture

`skills/` is the single source of truth. Supported agent hosts discover the same flat skill library through relative repository symlinks:

```text
.agents/skills -> ../skills
.claude/skills -> ../skills
.codex/skills  -> ../skills
.cursor/skills -> ../skills
.github/skills -> ../skills
```

The planned engagement workspace lives in SharePoint/OneDrive.


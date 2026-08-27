# Ascent Discovery AI Skill Library

This repository contains a reusable, host-neutral Discovery AI skill library and an accelerated-delivery Opportunity workspace template.

## Status

The initial setup, project-context, workspace knowledge, and Slalom branding workflows are implemented. Other TODO-marked skill packages remain scaffolds and must not be treated as approved executable guidance.

The implemented workspace workflow is:

1. `initial-setup` creates or resumes an Opportunity's standard `workspace/`, verifies Python 3.10+, records Account and Opportunity source locations, and initializes trackers.
2. `workspace-ingest-documents` turns source material — including meeting transcripts and raw notes — into filed workspace evidence and proposed tracker updates.
3. `workspace-review-updates` provides a local visual inbox and applies only changes approved by the user.
4. `workspace-summarize` produces evidence-grounded narrative outputs inside `workspace/`.

Use `slalom-branding` to apply or review approved Slalom colors, typography, accessibility, voice, imagery, logos, and graphic elements across deliverables.

## Architecture

`skills/` is the single source of truth. Supported agent hosts discover the same flat skill library through relative repository symlinks:

```text
.agents/skills -> ../skills
.claude/skills -> ../skills
.codex/skills  -> ../skills
.cursor/skills -> ../skills
.github/skills -> ../skills
```

The Opportunity workspace is designed to live in a SharePoint folder synchronized locally through OneDrive. Agent-created project work remains under the Opportunity's `workspace/` folder.

See [Opportunity Workspace Walkthrough](docs/opportunity-workspace-walkthrough.md) for the complete setup and daily operating flow.

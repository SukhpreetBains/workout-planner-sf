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

The planned engagement workspace lives in SharePoint/OneDrive. The Engagement folder is the project root and must not be wrapped in a checked-in `knowledge-hub/` directory.

## Primary skills

```text
setup
sales-handoff
mobilize
stakeholder-analysis
discovery-session
discovery-survey
analyze-org
architecture
capability-mapping
business-case
product-planning
ai-strategy
discovery
persona-journey
risk-management
governance-operating-model
change-strategy
delivery-planning
devops-security
test-strategy
data-migration-strategy
```

See [WORKFLOW.md](WORKFLOW.md) for the intended lifecycle. Installation guidance is deferred until the skill implementations and cross-host validation exist.

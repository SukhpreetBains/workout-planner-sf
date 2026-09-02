# Ascent

Ascent is an AI skill library for accelerated delivery of Discovery engagements. It gives a non-technical business user a governed, evidence-backed way to run an Opportunity: project knowledge is captured in a structured `workspace/`, every tracker change is traceable to a source document and approved by a human, and polished client deliverables are generated from that approved knowledge.

The skills are host-neutral. Any supported agent host (Claude Code, Codex, Cursor, GitHub Copilot) uses the same flat library in `plugins/ascent/skills/`, distributed through the self-contained Ascent plugin.

See [Installing and updating Ascent](docs/installation-and-updating.md) to add the plugin to an agent host or refresh an existing installation.

## How a project gets set up

Run `initial-setup` once when you start a new Opportunity or join an existing one. At a high level it:

1. Verifies that you have Python installed and that it is on the right version
2. Helps resolve the Opportunity's SharePoint Account folder and guides you through syncing it locally
3. Creates (or resumes) the standard Opportunity folder: a `workspace/` for all agent-created work and a `Deliverables/` folder for human-promoted final material.
4. Records project context, including Account, Opportunity, engagement type, objectives, and the confirmed external sources (SharePoint, Slack, Microsoft Teams locations) the project draws on.
5. Initializes the workspace engine: a local Python environment, four Excel trackers (`stakeholders`, `current-state`, `future-state`, `raid`), a full-text search index, and the proposed/applied update queues.

Setup is resumable and non-destructive: it shows a read-only check of what exists before changing anything, and it never overwrites existing files or tracker rows.

## The daily knowledge loop

Once set up, project knowledge flows through three skills. This is the core loop you repeat throughout the engagement:

```text
New documents land in workspace/inbox/
        ↓
workspace-ingest-documents   files them, writes session notes, proposes tracker updates
        ↓
workspace-review-updates     you approve, edit, or reject each proposal
        ↓
workspace-summarize          produces narratives from the approved knowledge
```

The separation is deliberate: ingestion never writes to the trackers, and `workspace-review-updates` is the **only** workflow authorized to change them. Every tracker row traces back to source evidence you approved.

## Which skills to call, and when

### Project workspace (the core workflow)

| Skill | Call it when |
| --- | --- |
| `initial-setup` | You are starting a new Opportunity or joining an existing one. Run this first; it is safe to re-run. |
| `workspace-ingest-documents` | New source material has arrived, such as meeting transcripts, notes, or client documents. Drop files into `workspace/inbox/` first. |
| `workspace-review-updates` | Proposed tracker updates are waiting for review. Presents each change with its evidence for approval, editing, or rejection. |
| `workspace-summarize` | You need a narrative from the workspace: current-state picture, weekly rollup, stakeholder view, or topic deep-dive. Read-only. |

### Gathering source material

| Skill | Call it when |
| --- | --- |
| `investigate-project` | You are onboarding to an unfamiliar project and need to map where its knowledge lives (folders, channels, stakeholders, terminology), or you need cited evidence from those known sources for a specific question. |

The planned `download-teams-transcripts` skill is not yet an executable workflow.

### Planned deliverable capabilities

The following skills are present as planned work but are not executable workflows or approved delivery guidance yet.

| Skill | Intended use after implementation |
| --- | --- |
| `create-deliverables` | A discovery readout, findings summary, roadmap, or business case should be delivered as an interactive Slalom-branded web microsite. |
| `compose-deliverable` | The same content should instead be a native, editable Slalom-branded PowerPoint deck. Uses the same approved content as the microsite. |

### Planned situational utilities

The following skills are also planned and are not executable workflows yet.

| Skill | Intended use after implementation |
| --- | --- |
| `analyze-org` | You need an architecture map of a Salesforce org, including what features, objects, and automation exist, expressed in the org's own vocabulary. |
| `interview-me` | You want your plan or design stress-tested through a rigorous Q&A before committing to it. |
| `recursive-improvement` | A workflow went wrong or needed correction, and you want the lessons turned into durable improvements to the skills and guidance. |
| `design-skill-evals` | You are building or maintaining a skill and need an evaluation package for it (correctness, cost, time saved). Contributor-facing. |

## Repository layout

```text
plugins/ascent/   Self-contained plugin and authoritative skill library
docs/             Guides, including installation and the full workspace walkthrough
evals/            Evaluation packages for the skills (contributor-facing)
tests/            Acceptance tests
```

Note that the Opportunity workspace itself does **not** live in this repository. It lives in the Opportunity's SharePoint folder, synced locally through OneDrive.

## Further reading

- [Installing and updating Ascent](docs/installation-and-updating.md), host-specific installation and update instructions.
- [Opportunity Workspace Walkthrough](docs/opportunity-workspace-walkthrough.md), the complete setup and daily operating flow, step by step.
- [Ascent evaluations](evals/README.md), how skill evaluation packages are designed and run (for contributors).

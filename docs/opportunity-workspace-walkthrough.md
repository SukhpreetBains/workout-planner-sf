# Opportunity Workspace Walkthrough

This guide explains how initial setup and the workspace skills work together from Opportunity creation through ongoing knowledge management.

## 1. Run `initial-setup`

Start with an existing SharePoint Account folder. The skill:

1. Verifies Python 3.10 or newer.
2. Resolves the SharePoint Account location.
3. Guides the user through connecting it to OneDrive when necessary.
4. Asks whether the user is starting a new Opportunity or joining an existing one.
5. Confirms the Account name, Opportunity name, synced local path, user-reported SharePoint Edit access, and local write readiness.

Before changing anything, setup runs a read-only check showing what exists and what is missing.

## 2. Prepare the Opportunity folder

Setup copies the canonical workspace template bundled with `initial-setup` into the Opportunity:

```text
<Account>/
  <Opportunity>/
    AGENTS.md
    workspace/
      inbox/
      project/
      meetings/
      current-state/
      future-state/
      reference/
      trackers/
      .system/
    Deliverables/
      Mobilize/
      Discover/
      Deliver/
      Transition/
```

The operation is resumable. Existing files and tracker rows are preserved, while missing template files and folders are created. All agent-created project work stays inside `workspace/`. A person can promote reviewed material into `Deliverables/`.

## 3. Capture Opportunity details

Machine-readable project data goes into `workspace/.system/project.yaml`:

```yaml
account: <account name>
opportunity: <opportunity name>
engagement_type: <type>
summary: <summary>
dates: <dates>
current_focus: <focus>
```

The readable version goes into `workspace/project/Project Overview.md`, including the Account, Opportunity, engagement type, Slalom lead, Opportunity sponsor, objectives, scope, systems, and success metrics.

## 4. Record external project locations

Setup can identify relevant SharePoint, Slack, and Microsoft Teams locations. It asks before saving confirmed locations to:

```text
workspace/.system/source-context.yaml
```

This project communications record contains source locations and access state, not message bodies, document contents, credentials, or copied files.

It is separate from `workspace/.system/sources.yaml`, which inventories individual documents ingested into the workspace.

## 5. Initialize the workspace engine

Setup initializes:

- the Python environment at `workspace/.system/.venv/`
- four Excel tracker workbooks
- plain-text tracker copies
- the full-text search index
- proposed and applied update queues

The trackers are:

- `stakeholders.xlsx`
- `current-state.xlsx`
- `future-state.xlsx`
- `raid.xlsx`

## 6. Ingest documents and capture meetings

Place new material in `workspace/inbox/`, then invoke `workspace-ingest-documents`.

The skill:

1. Reads or converts each document.
2. For a meeting transcript or raw notes, writes a structured session note under `workspace/meetings/` and files the transcript beside it. For everything else, files it into `current-state/`, `future-state/`, or `reference/`.
3. Records it in `workspace/.system/sources.yaml`.
4. Extracts evidence-backed stakeholders, pain points, systems, objectives, requirements, risks, assumptions, issues, decisions, dependencies, constraints, and open questions.
5. Writes proposed changes into `workspace/.system/proposed-updates/`.
6. Validates the proposals and refreshes the search index.

It does not modify the trackers.

## 7. Review proposed updates

Invoke `workspace-review-updates` to inspect pending changes. For each proposal, it shows:

- a loopback-only visual review link when proposals are ready
- category counts and a completed-versus-remaining progress bar
- one governed proposal card at a time, with autosaved edits and source evidence

- the proposed addition or change
- supporting source evidence
- whether it is a new row or an update
- the existing tracker row when applicable

The user can approve, edit, or reject each proposal. Only approved changes are written into the Excel trackers. Applied proposal files move to `workspace/.system/applied-updates/`.

This is the only skill authorized to write tracker changes.

## 8. Summarize workspace knowledge

Invoke `workspace-summarize` for current-state summaries, weekly rollups, stakeholder views, system or process deep dives, and future-state summaries.

The skill searches workspace documents and tracker rows, traces important claims to their sources, identifies contradictions and gaps, and can write results beneath `workspace/current-state/` or `workspace/future-state/`. It never changes the trackers.

## Ongoing workflow

```text
New documents
    ↓
workspace-ingest-documents
    ↓
Proposed tracker updates
    ↓
workspace-review-updates
    ↓
Approved tracker knowledge
    ↓
workspace-summarize
```

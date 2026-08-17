# Accelerated Delivery Template

A project template for AI-assisted discovery and delivery work. You drop
client documents in, the agent extracts what matters into structured
trackers, you approve every change, and everything stays searchable and in
sync as new material arrives.

See [Opportunity Workspace Walkthrough](WORKSPACE-WALKTHROUGH.md) for the complete setup and operating flow.

Open the Opportunity folder in a supported agent host and invoke the skills
by name. The host-neutral skill source lives in `skills/` and may be exposed
through the host-specific skill symlink.

## How it works

```
documents in workspace/inbox/
        │
        ▼
 workspace-ingest-documents       files each document, extracts findings
 workspace-capture-meeting-notes  (stakeholders, pain points, systems, risks,
        │                   requirements, decisions, questions, ...)
        ▼
 proposed updates          waiting in workspace/.system/proposed-updates/
        │
        ▼
 workspace-review-updates  you approve, edit, or reject each one;
        │                  approved rows are written to the trackers
        ▼
 workspace/trackers/       four Excel workbooks — the project's memory
        │
        ▼
 sync                      search index + plain-text tracker copies,
        │                  rebuilt automatically after every change
        ▼
 workspace-summarize       narrative answers grounded in the evidence
```

Every tracker row cites the document it came from, and nothing reaches a
tracker without human approval.

## Getting started

1. Run `initial-setup` for the Account and Opportunity. It verifies Python
   3.10+, creates or resumes this workspace structure, and initializes the
   trackers without overwriting existing files.
2. Open the Opportunity folder in a supported agent host.
3. **Drop any starting materials** (SOW, proposals, org charts, notes)
   into `workspace/inbox/`.
4. Invoke `workspace-ingest-documents` to file documents and propose the
   first tracker updates.
5. Invoke `workspace-review-updates` to approve what goes into the trackers.

## The daily loop

1. New documents → `workspace/inbox/` → `workspace-ingest-documents`
2. After a meeting → `workspace-capture-meeting-notes` with the transcript
3. `workspace-review-updates` to approve proposed changes
4. `workspace-summarize` when you need the story so far

## What lives where

| Path | What it is |
| --- | --- |
| `workspace/inbox/` | Drop zone for new, unprocessed documents |
| `workspace/project/` | Project overview, timeline, phase context |
| `workspace/meetings/` | Session notes and transcripts, date-prefixed |
| `workspace/current-state/` | How things work today |
| `workspace/future-state/` | Where things are heading |
| `workspace/reference/` | Background material (SOWs, exports, client docs) |
| `workspace/trackers/` | Four Excel trackers: stakeholders, current-state (pain points + systems), future-state (objectives + requirements), raid (risks, assumptions, constraints, decisions, open questions) |
| `workspace/.system/` | Machine-managed: proposed/applied updates, search index, plain-text tracker copies, sync state |
| `skills/` | The host-neutral workflows plus `_shared/` (the schema and engine scripts they use) |

The tracker schema — every category, column, and allowed value, with
plain-English definitions of what belongs — is one file:
`skills/_shared/schema/trackers.yaml`.

## Useful commands

The engine can also be driven directly (`PY` = `skills/_shared/scripts/py`)
with `EAD_REPO_ROOT` set to the Opportunity folder:

```bash
PY skills/_shared/scripts/sync.py --status   # what's new / not yet processed?
PY skills/_shared/scripts/search.py "billing handoff"
PY skills/_shared/scripts/search.py --id PAIN-003
```

Trackers are normal Excel files — open and edit them by hand whenever you
like, then run `sync.py` so the index catches up.

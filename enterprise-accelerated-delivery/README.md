# Accelerated Delivery Template

A project template for AI-assisted discovery and delivery work. You drop
client documents in, the agent extracts what matters into structured
trackers, you approve every change, and everything stays searchable and in
sync as new material arrives.

Built for Claude Code: open this folder, and the skills in
`.agents/skills/` do the work.

## How it works

```
documents in workspace/inbox/
        │
        ▼
 /add-documents            files each document, extracts findings
 /add-meeting-notes        (stakeholders, pain points, systems, risks,
        │                   requirements, decisions, questions, ...)
        ▼
 proposed updates          waiting in workspace/.system/proposed-updates/
        │
        ▼
 /review-updates           you approve, edit, or reject each one;
        │                  approved rows are written to the trackers
        ▼
 workspace/trackers/       four Excel workbooks — the project's memory
        │
        ▼
 sync                      search index + plain-text tracker copies,
        │                  rebuilt automatically after every change
        ▼
 /summarize                narrative answers grounded in the evidence
```

Every tracker row cites the document it came from, and nothing reaches a
tracker without human approval.

## Getting started

1. **Clone this template** into a folder for your engagement
   (`git clone <repo-url> acme-discovery`). Python 3.10+ must be
   installed; everything else is handled automatically.
2. **Open the folder in Claude Code.**
3. **Drop any starting materials** (SOW, proposals, org charts, notes)
   into `workspace/inbox/`.
4. **Type `/setup`** and answer a few plain-English questions about the
   project. Setup prepares the environment, creates the trackers, files
   your documents, and proposes the first tracker updates.
5. **Type `/review-updates`** to approve what goes into the trackers.

## The daily loop

1. New documents → `workspace/inbox/` → `/add-documents`
2. After a meeting → `/add-meeting-notes` with the transcript
3. `/review-updates` to approve proposed changes
4. `/summarize` when you need the story so far

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
| `.agents/skills/` | The five workflows plus `_shared/` (the schema and engine scripts they all use) |

The tracker schema — every category, column, and allowed value, with
plain-English definitions of what belongs — is one file:
`.agents/skills/_shared/schema/trackers.yaml`.

## Useful commands

The engine can also be driven directly (`PY` =
`.agents/skills/_shared/scripts/py`):

```bash
PY .agents/skills/_shared/scripts/sync.py --status   # what's new / not yet processed?
PY .agents/skills/_shared/scripts/search.py "billing handoff"
PY .agents/skills/_shared/scripts/search.py --id PAIN-003
```

Trackers are normal Excel files — open and edit them by hand whenever you
like, then run `sync.py` so the index catches up.

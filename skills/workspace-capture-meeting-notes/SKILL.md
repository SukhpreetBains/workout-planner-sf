---
name: workspace-capture-meeting-notes
description: Turn a meeting transcript or raw notes into a structured session note in workspace/meetings/, record its provenance, extract evidence-backed proposed tracker updates, and refresh the search index. Use after workshops, interviews, standups, or other project sessions in an initialized Opportunity workspace.
---

# Capture Workspace Meeting Notes

One meeting in, two things out: a readable session note filed in
`workspace/meetings/`, and proposed tracker updates for review.

Locate `skills/_shared` alongside the installed skill library. Set
`EAD_REPO_ROOT` to the Opportunity folder for every engine command, then
run scripts through `_shared/scripts/py` or `_shared/scripts/py.cmd`.

## Step 1 — Get the raw material

The input is a transcript or notes file (often in `workspace/inbox/`, or a
path the user gives). If it is `.docx`/`.pdf`, convert it first with
`PY <shared-skill-dir>/scripts/read_document.py "<path>" --out "<path>.md"`.
Ask the user for the meeting date, attendees, and purpose if the file does
not say.

## Step 2 — Write the session note

Create `workspace/meetings/YYYY-MM-DD - <Meeting Title>.md` using the
template in `references/session-note-template.md`. Summarize faithfully —
capture what was said, who said it, and what was decided or left open. Move
the raw transcript to `workspace/meetings/` alongside the note (same date
prefix, ` - transcript` suffix) so the note can cite it.

Record both files in `workspace/.system/sources.yaml` (the transcript as
the source, `status: extracted` once Step 3 is done).

## Step 3 — Extract findings

Follow the extraction procedure in `workspace-ingest-documents` against the session note and
transcript: collect findings per the categories in
`<shared-skill-dir>/schema/trackers.yaml`, write a proposed-updates
file, and validate it. Use the session note (not the transcript) as the
primary `source_refs` entry.

Meetings are the richest source of decisions, open questions, and
stakeholder signals — check those three categories deliberately before
finishing.

## Step 4 — Sync and hand off

Run `PY <shared-skill-dir>/scripts/sync.py`, then tell the user where
the note lives, what was proposed, and that `workspace-review-updates` is next.

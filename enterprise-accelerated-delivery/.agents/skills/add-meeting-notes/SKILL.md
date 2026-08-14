---
name: add-meeting-notes
description: Turn a meeting transcript or raw notes into a structured session note in workspace/meetings/, then extract findings from it into proposed tracker updates. Use after workshops, interviews, standups, or any client session.
---

# Add meeting notes

One meeting in, two things out: a readable session note filed in
`workspace/meetings/`, and proposed tracker updates for review.

Shorthand: `PY` = `.agents/skills/_shared/scripts/py`; engine scripts live
in `.agents/skills/_shared/scripts/`.

## Step 1 — Get the raw material

The input is a transcript or notes file (often in `workspace/inbox/`, or a
path the user gives). If it is `.docx`/`.pdf`, convert it first with
`PY .agents/skills/_shared/scripts/read_document.py "<path>" --out "<path>.md"`.
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

Follow Step 3 of the **add-documents** skill
(`.agents/skills/add-documents/SKILL.md`) against the session note and
transcript: collect findings per the categories in
`.agents/skills/_shared/schema/trackers.yaml`, write a proposed-updates
file, and validate it. Use the session note (not the transcript) as the
primary `source_refs` entry.

Meetings are the richest source of decisions, open questions, and
stakeholder signals — check those three categories deliberately before
finishing.

## Step 4 — Sync and hand off

Run `PY .agents/skills/_shared/scripts/sync.py`, then tell the user where
the note lives, what was proposed, and that `/review-updates` is next.

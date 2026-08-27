---
name: workspace-ingest-documents
description: Process new documents from workspace/inbox/ by filing them in the workspace, turning meeting transcripts or raw notes into a structured session note, recording everything in the document-source ledger, extracting evidence-backed tracker updates, validating the proposals, and refreshing the search index. Use whenever new project source material arrives, including after workshops, interviews, standups, or other project sessions, in an initialized Opportunity workspace.
---

# Ingest Workspace Documents

Turn whatever landed in `workspace/inbox/` into filed documents (plus a
structured session note for meeting material) and proposed tracker
updates. Nothing is written to the trackers here; that only happens
after the user approves through `workspace-review-updates`.

Locate `skills/_shared` alongside the installed skill library. Set
`EAD_REPO_ROOT` to the Opportunity folder for every engine command, then
run scripts through `_shared/scripts/py` or `_shared/scripts/py.cmd`.

## Step 1 — Read each inbox file

List `workspace/inbox/`. For each file:

- Plain text (`.md`, `.txt`, `.csv`, …): read it directly.
- `.docx`, `.pdf`, `.pptx`, `.xlsx`: convert first —
  `PY <shared-skill-dir>/scripts/read_document.py "workspace/inbox/<file>" --out "workspace/inbox/<file stem>.md"`
  and read the Markdown. Keep the converted `.md` next to where the
  original will be filed; it is the readable copy.

Only ask the user when a file is genuinely ambiguous — including whether something is meeting material or an ordinary document.

## Step 2 — File it

### Meeting or workshop material (transcripts, raw notes)

Ask the user for the meeting date, attendees, and purpose if the file
itself does not state them. Write a session note to
`workspace/meetings/YYYY-MM-DD - <Meeting Title>.md` using the template
in `references/session-note-template.md`. Summarize faithfully — capture
what was said, who said it, and what was decided or left open, keeping
the client's own vocabulary rather than translating it.

Move the raw transcript alongside the note in `workspace/meetings/`,
same date prefix, ` - transcript` suffix, so the note can cite it. Record
both files in `workspace/.system/sources.yaml` (the transcript as the
source, `status: extracted` once Step 3 is done for it).

### Everything else

Move the file (and its converted `.md`) out of the inbox to where it
belongs:

| Content | Destination |
| --- | --- |
| How things work today (process docs, system exports, org charts) | `workspace/current-state/` |
| Where things are heading (vision docs, solution options, scope) | `workspace/future-state/` |
| Background material (SOWs, proposals, client reference docs) | `workspace/reference/` |

Add one entry per document to `workspace/.system/sources.yaml`:

```yaml
sources:
  - path: workspace/reference/Acme SOW.pdf
    added: 2026-08-14
    status: extracted        # extracted | pending | skipped (say why)
    summary: One line on what the document is.
```

## Step 3 — Extract findings

Read `<shared-skill-dir>/schema/trackers.yaml`. It defines every
category (stakeholder, pain_point, system, objective, requirement, risk,
assumption, constraint, decision, open_question), what belongs in each,
the bar a finding must clear, and the exact columns and allowed values.

Go through each document — for meeting material, use the session note
(not the raw transcript) as the primary `source_refs` entry, and check
the decision, open_question, and stakeholder categories deliberately;
meetings are the richest source for those three. Collect every finding
that clears its category's bar. Check `workspace/.system/tracker-copies/`
for rows that already exist: propose an `update` to enrich an existing
row rather than an `add` that duplicates it, and use existing row IDs
when filling `... IDs` link columns.

Write one file per batch to
`workspace/.system/proposed-updates/<YYYY-MM-DD>-<short-topic>.yaml`:

```yaml
source_refs: ["workspace/reference/Acme SOW.pdf"]
updates:
  - category: pain_point
    action: add            # or: update (then also give `id: PAIN-003`)
    fields:
      Statement: Invoice approvals take 9 days because the handoff is manual.
      Pain Type: process
      Severity: high
    # source_refs: [...]   # per-update override when updates span documents
```

Validate, and fix anything it reports:

```
PY <shared-skill-dir>/scripts/validate_updates.py workspace/.system/proposed-updates/<file>.yaml
```

## Step 4 — Sync and hand off

Run `PY <shared-skill-dir>/scripts/sync.py`, then tell the user what
was filed (including where any session note lives), how many updates
were proposed per category, and that `workspace-review-updates` is the
next step. If the trackers are empty of stakeholders/systems that
findings need to link to, propose those rows in the same batch — order
within one file does not matter for validation of links to *existing*
rows, so link only to IDs that are already in the trackers and mention
the rest in Notes.

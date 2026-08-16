---
name: add-documents
description: Process new documents from workspace/inbox/ — file each one into the right workspace folder, record it in the source list, extract findings (stakeholders, pain points, systems, risks, requirements, and other tracker categories) into proposed updates for review, and re-sync the search index. Use whenever new source material arrives.
---

# Add documents

Turn whatever landed in `workspace/inbox/` into filed documents plus
proposed tracker updates. Nothing is written to the trackers here — that
only happens after the user approves in `/review-updates`.

Shorthand: `PY` = `.agents/skills/_shared/scripts/py`; engine scripts live
in `.agents/skills/_shared/scripts/`.

## Step 1 — Read each inbox file

List `workspace/inbox/`. For each file:

- Plain text (`.md`, `.txt`, `.csv`, …): read it directly.
- `.docx`, `.pdf`, `.pptx`, `.xlsx`: convert first —
  `PY .agents/skills/_shared/scripts/read_document.py "workspace/inbox/<file>" --out "workspace/inbox/<file stem>.md"`
  and read the Markdown. Keep the converted `.md` next to where the
  original will be filed; it is the readable copy.

## Step 2 — File it

Move each file (and its converted `.md`) out of the inbox to where it
belongs:

| Content | Destination |
| --- | --- |
| Meeting/workshop notes, transcripts | `workspace/meetings/` (prefix the name with the meeting date, `YYYY-MM-DD - Title`) |
| How things work today (process docs, system exports, org charts) | `workspace/current-state/` |
| Where things are heading (vision docs, solution options, scope) | `workspace/future-state/` |
| Background material (SOWs, proposals, client reference docs) | `workspace/reference/` |

Only ask the user when a file is genuinely ambiguous. Then add one entry
per document to `workspace/.system/sources.yaml`:

```yaml
sources:
  - path: workspace/reference/Acme SOW.pdf
    added: 2026-08-14
    status: extracted        # extracted | pending | skipped (say why)
    summary: One line on what the document is.
```

## Step 3 — Extract findings

Read `.agents/skills/_shared/schema/trackers.yaml`. It defines every
category (stakeholder, pain_point, system, objective, requirement, risk,
assumption, constraint, decision, open_question), what belongs in each,
the bar a finding must clear, and the exact columns and allowed values.

Go through each document and collect every finding that clears its
category's bar. Check `workspace/.system/tracker-copies/` for rows that
already exist: propose an `update` to enrich an existing row rather than
an `add` that duplicates it, and use existing row IDs when filling
`... IDs` link columns.

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
PY .agents/skills/_shared/scripts/validate_updates.py workspace/.system/proposed-updates/<file>.yaml
```

## Step 4 — Sync and hand off

Run `PY .agents/skills/_shared/scripts/sync.py`, then tell the user what
was filed, how many updates were proposed per category, and that
`/review-updates` is the next step. If the trackers are empty of
stakeholders/systems that findings need to link to, propose those rows in
the same batch — order within one file does not matter for validation of
links to *existing* rows, so link only to IDs that are already in the
trackers and mention the rest in Notes.

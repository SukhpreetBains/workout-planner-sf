---
name: add-documents
description: Process new documents from workspace/inbox/ by filing them in the workspace, turning meeting transcripts or raw notes into a structured session note, recording everything in the document-source ledger, extracting evidence-backed tracker updates, validating the proposals, and refreshing the search index. Use whenever new project source material arrives, including after workshops, interviews, standups, or other project sessions, in an initialized Opportunity workspace.
---

# Add Project Documents

Turn whatever landed in `workspace/inbox/` into filed documents (plus a
structured session note for meeting material) and proposed tracker
updates. Nothing is written to the trackers here; that only happens
after the user approves through `review-updates`.

Locate `shared/` at the installed Ascent plugin root. Set
`ASCENT_OPPORTUNITY_ROOT` to the Opportunity folder for every engine command, then
run scripts through `shared/scripts/py` or `shared/scripts/py.cmd`.

Before anything else, confirm the workspace is initialized:

```
PY <shared-skill-dir>/scripts/sync.py --check-setup
```

This is a cheap, read-only filesystem check. If it reports the workspace as
not ready, stop here and tell the user this doesn't look like an initialized
Opportunity workspace — offer to hand off to `initial-setup` first.

## Step 1 — Read each inbox file

List `workspace/inbox/`. For each file:

- Plain text (`.md`, `.txt`, `.csv`, …): read it directly.
- `.docx`, `.pdf`, `.pptx`, `.xlsx`: convert first —
  `PY <shared-skill-dir>/scripts/read_document.py "workspace/inbox/<file>" --out "workspace/inbox/<file stem>.md"`
  and read the Markdown. Keep the converted `.md` next to where the
  original will be filed; it is the readable copy.

Only ask the user when a file is genuinely ambiguous — including whether something is meeting material or an ordinary document.

### Parallel extraction for multi-document batches

When the inbox contains two or more independent source documents, group them by
their lifecycle relationship or subject matter, then delegate each group to one
subagent. On a host that supports subagent model selection, use
`gpt-5.6-luna` with `high` reasoning effort for every such subagent. On other
hosts, use the closest available subagent configuration without claiming that a
specific model or reasoning setting was applied.

Give each subagent only its assigned files and the tracker schema. It may read
or convert those files, classify each as meeting material or ordinary
reference/current-state/future-state material, and return candidate findings
with short verbatim evidence. It must not move files, write session notes or
the source ledger, create or edit proposal YAML, run sync or the review server,
or write to trackers.

The parent agent keeps control of filing, source-ledger updates, duplicate
resolution against tracker copies, proposal creation and validation, sync, and
the approval-gated tracker workflow. Consolidate every subagent result before
creating a batch proposal so related documents produce one coherent, deduped
set of proposed facts.

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
    proposal_id: "<uuid>"    # stable across edits and review
    revision: 1
    action: add            # or: update (then also give `id: PAIN-003`)
    fields:
      Statement: Invoice approvals take 9 days because the handoff is manual.
      Pain Type: process
      Severity: high
    evidence:
      - source_ref: workspace/meetings/2026-08-14 - Kickoff.md
        excerpt: "Invoice approvals take 9 days because the handoff is manual."
        line_start: 42       # optional when line information is available
        line_end: 42
    # source_refs: [...]   # per-update override when updates span documents
```

Validate, and fix anything it reports:

```
PY <shared-skill-dir>/scripts/validate_updates.py workspace/.system/proposed-updates/<file>.yaml
```

Use a UUID for every `proposal_id`. Increment `revision` whenever an agent
rewrites a proposal after it has been created. Evidence excerpts must be short,
verbatim support for the specific proposal. Do not manufacture line numbers.

## Step 4 — Sync and hand off

Run `PY <shared-skill-dir>/scripts/sync.py`. If validation produced one or more
proposals, run:

```
PY <shared-skill-dir>/scripts/review_server.py start --root "$ASCENT_OPPORTUNITY_ROOT"
```

The command health-checks and reuses a running inbox or safely replaces stale
state. Post its loopback URL in chat as, for example, "7 new items ready for
review." Never open the browser automatically. If there are no proposals, do
not start the server and do not post an app alert.

Then give the user a clear,
plain-English handoff. Do not merely mention a workflow or leave the next
step implicit. State:

- that the project trackers have **not** been changed yet;
- the total number of evidence-backed items ready for their review, with
  counts by category;
- that these are proposed facts, not yet the project's official working
  record, and need their approval before they are added; and
- the exact next action in user language: for example, “I have 16 items
  ready for your approval. Would you like me to review and populate the
  project trackers now?”

If the user approves, invoke `review-updates` and walk the
proposals through its governed review. If they do not approve, leave the
proposals in place and make clear that they are available for a later
review. Also report what was filed (including where any session note
lives). If the trackers are empty of stakeholders/systems that findings
need to link to, propose those rows in the same batch - order within one
file does not matter for validation of links to *existing* rows, so link
only to IDs that are already in the trackers and mention the rest in
Notes.

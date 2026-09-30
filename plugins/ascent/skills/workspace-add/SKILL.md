---
name: workspace-add
description: Process new documents from workspace/inbox/ by filing them in the workspace, turning meeting transcripts or raw notes into a structured session note, recording everything in the document-source ledger, extracting evidence-backed tracker updates, validating the proposals, and refreshing the search index. Use whenever new project source material arrives, including after workshops, interviews, standups, or other project sessions, in an initialized Opportunity workspace.
---

# Workspace Add

Turn whatever landed in `workspace/inbox/` into filed documents (plus a
structured session note for meeting material) and proposed tracker
updates. Nothing is written to the trackers here; that only happens
after the user approves through `workspace-review`.

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

If it also prints an `ascent update:` line, pass that message to the user once, in
plain words, and carry on. It is either a downloaded update waiting for a Codex
relaunch or a note that background updates are stuck; it never blocks the
current work.

## Industry flavor

Check `workspace/.system/project.yaml` for an `industry:` key.

- **Absent entirely** — this Opportunity has never been asked. Scan
  `shared/industry/*/manifest.json` for available packs. If any exist, ask
  once, offering each by title plus a "none of these" option, and write
  whichever the user picks (an id, or `none`) into `project.yaml`,
  preserving every other key. If no packs exist, skip this silently.
- **`none`** — asked and declined already. Proceed exactly as documented
  below, no different from this section not existing. Do not ask again.
- **An id** — read that pack's `references/ingestion-guidance.md`
  (`shared/industry/<id>/manifest.json` names its exact path) and apply it
  alongside Steps 2–4 below as emphasis and framing, including passing it
  to each curation subagent. It never adds a
  tracker category or column, and it never overrides a direct
  in-conversation instruction for this turn (e.g. "don't apply industry
  flavor here").

Read [../../shared/industry/README.md](../../shared/industry/README.md) for
the full contract if anything here is ambiguous.

## Step 1 — Select a batch of up to three documents

```
PY <shared-skill-dir>/scripts/select_inbox_batch.py
```

It returns at most three original sources in `selected` — oldest
modification time first, filename breaking ties — and how many originals
`remaining`. A converted `.md` beside its original (`Report.md` next to
`Report.pdf`) is reported as that original's `converted_copy` and never
counts as a separate source. Work only on `selected`; everything else stays
in the inbox until its own batch.

Run Steps 2–4 for this batch, then run the selector again and repeat until
`selected` comes back empty. Proceed to Step 5 once, after the last batch.
If the selector returns a document that was already selected earlier in
this run, stop looping and report it to the user instead of retrying.

## Step 2 — Curate each document separately

Before dispatching, convert any selected `.docx`, `.pdf`, `.pptx`, or `.xlsx`
that has no `converted_copy`:

```
PY <shared-skill-dir>/scripts/read_document.py "workspace/inbox/<file>" --out "workspace/inbox/<file stem>.md"
```

Keep the converted `.md` beside its original; it is the readable copy and
is filed with it.

Give every selected document **its own fresh** curation subagent — one
document per subagent, never grouped, so each gets undivided attention.
Start the batch's subagents in parallel, up to three at once.

Every subagent starts clean and handles exactly one document in its
lifetime:

- Do not give it the parent's conversation history or any other
  document's content or findings.
- Never hand a later document to a subagent that already worked on one —
  no follow-up or continuation messages to reuse it.
- Close each subagent once its result is back. The next batch gets new
  subagents.

Connecting findings across documents is the parent's job in Step 4, not
the subagents'.

Use the latest suitable low-cost model the host offers for subagents (for example
a current GPT Luna or Claude Haiku model), with high reasoning effort when
the host supports setting it. Never claim a model or reasoning setting the
host did not actually apply.

Give each subagent only its one document (original plus converted copy),
`<shared-skill-dir>/schema/trackers.yaml`, and the active industry pack's
ingestion guidance if one applies. It reads the document, classifies it as
meeting material or current-state / future-state / reference material, and
returns:

- the classification;
- candidate findings, each with its category, proposed field values, and
  source-linked evidence — the `source_ref` plus a short verbatim
  `excerpt` that on its own supports the whole finding (a heading or label
  alone is not evidence; line numbers only when actually known);
- a `basis` on every finding: `stated` when the excerpt says it directly,
  or `inferred` when it is a reading between the lines, naming what it was
  inferred from.

For meeting material, the subagent checks five categories deliberately:
decisions, open questions, stakeholders, action items, and risks.

For a contract, statement of work, or services schedule, the subagent
returns every stated fee, cap or limit, scope exclusion, dependency, and
date as its own finding, not just the headline ones. Lists of limits and
exclusions are easy to skim past, and each item is what the team later
checks scope against.

A curation subagent must not move files, write session notes or the source
ledger, create or edit proposal YAML, run sync or the review server, or
write to trackers.

**Fallback.** If the host cannot provide suitable subagents, the parent
curates each selected document itself, one at a time, under exactly the same
rules and return shape — never reading the batch as one combined pass — and
tells the user in the handoff that curation ran without subagents.

## Step 3 — File it

Use each subagent's classification. Only ask the user when a document is
genuinely ambiguous — including whether it is meeting material or an
ordinary document. If a document cannot be processed, record it in
`sources.yaml` as `status: skipped` with the reason and tell the user.

### Meeting or workshop material (transcripts, raw notes)

Ask the user for the meeting date, attendees, and purpose if the file
itself does not state them. Write a session note to
`workspace/meetings/YYYY-MM-DD - <Meeting Title>.md` using the template
in `references/session-note-template.md`. Summarize faithfully — capture
what was said, who said it, and what was decided or left open, keeping
the client's own vocabulary rather than translating it.

List every distinct action from the source under Follow-ups, each with its
owner and timing as stated. Do not merge or drop actions, and keep every
risk the source raises. Proposals cite this note, so anything left out here
never reaches review.

Move the raw transcript alongside the note in `workspace/meetings/`,
same date prefix, ` - transcript` suffix, so the note can cite it. Record
both files in `workspace/.system/sources.yaml` (the transcript as the
source, `status: extracted` once Step 4 is done for it).

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

## Step 4 — Reconcile and propose

The parent turns the batch's curated findings into proposals. Read
`<shared-skill-dir>/schema/trackers.yaml`: it defines every category, what
belongs in each, the bar a finding must clear, and the exact columns and
allowed values.

Work from what the subagents returned:

- Build proposals from the subagents' findings. Do not re-extract a
  document yourself unless its subagent failed on it; if you do, say so in
  the handoff.
- Every candidate you drop needs a short reason: a duplicate of a named
  item, superseded by a named later source, or below its category's bar.
- Drop a candidate as superseded only after confirming the stronger source
  covers it. If that source's findings do not include the term, check the
  source's text yourself. When the term is there, keep the finding and cite
  the stronger source. When it is not, drop the candidate with the reason
  "not in <source>".
- Never remove proposals in bulk by source document. Judge each item on
  its own — a document can be partly superseded and still hold open,
  relevant findings.

Reconcile before proposing:

- **Across documents** — merge findings that describe the same fact into
  one proposal carrying evidence from each document.
- **Against existing tracker rows** — check
  `workspace/.system/tracker-copies/`; propose an `update` to enrich an
  existing row rather than an `add` that duplicates it, and use existing
  row IDs when filling `... IDs` link columns.
- **Against earlier batches in this run** — tracker copies do not show
  pending proposals, so also check the proposal files already written this
  run and extend those instead of duplicating them.

**Stakeholders are named people.** Propose a stakeholder row only for a
named person. When a source describes a role without naming who fills it
("Experian technical lead"), propose an `open_question` asking who fills
it, or an `action_item` to assign someone, instead. When a later document
names the person behind a role an earlier batch in this run recorded,
revise that earlier proposal (incrementing its `revision`) rather than
adding a second row; if the role is already an approved tracker row,
propose an `update` to it.

**When sources disagree**, the stronger source wins:

1. signed or executed documents over drafts and redlines;
2. later-dated documents over earlier ones;
3. delivery-phase documents (kickoff materials, meeting notes) over
   pre-sale ones (RFQ responses, proposals) for plans, roles, and dates.

When a later document contradicts a signed one with no evidence of a
formal change, keep the signed value and propose an `open_question` naming
both sources.

**Title every risk, assumption, issue, decision, and dependency.** The
`… Title` column is required: a short summary of three to eight words that
names the item, written fresh rather than copied or cut from the statement.
For example, "Single-point routing through Danielle" for a risk whose
statement explains how relying on one Experian contact for every request
could slow decisions, or "Standard data model first" for a decision to
extend Salesforce's standard model before building a custom one. The
validator rejects a missing title, a title that repeats the statement, and
one that ends in "…".

**Classify by what the finding is:**

- Caps, limits, and exclusions are constraints. "Up to" scope limits, fees
  and fee caps, contracted date windows, and scope exclusions are a
  `constraint` (contractual, budget, or timeline), not a `requirement`;
  requirements are what the solution or delivery must do.
- Internal Slalom commercial material stays out of the trackers. Do not
  propose pricing-tool guidance, rates, margins, contingencies, or internal
  cost structures. File and log the document as usual and say in the
  handoff that it was filed without proposals. Commercial terms in a
  signed client agreement are client-agreed and remain valid budget
  constraints.
- Plan items keep the status their source states. Never set `complete` or
  `delayed` without a source saying so. Propose milestones whose date has
  passed like any others, and also list them in the handoff as having no
  confirmed outcome.
- A RACI becomes one `operating_model` row per activity (`Model Type:
  responsibility_assignment`). While its parties are organizations or teams
  rather than named people, record each party's letter in `Activity` (for
  example "RACI: ECS Business C; Slalom R"); use the Responsible,
  Accountable, Consulted, and Informed link columns once a named
  stakeholder holds the role.
- Kickoff decks, talk tracks, and agendas describe intentions. Their next
  steps and agenda topics become `action_item`s only when the source states
  an owner or a commitment; otherwise propose them as `plan_item`s or not at
  all. Never propose notes aimed at the presenter or about the document
  itself.

**Linking to rows that do not exist yet.** When a finding links to a
stakeholder, system, or other row that is not in the trackers, propose that
row as well and put its `proposal_id` in the link column (`;`-separated
alongside any existing IDs). It may come from this batch or an earlier batch
in this run. The review inbox swaps it for the real tracker ID when that row
is approved and removes it if the row is rejected.

Subagents cite `workspace/inbox/...` paths, but Step 3 has since filed those
documents; rewrite every `source_ref` to the document's filed location (or
its session note) before writing proposals.

Propose only findings that clear their category's bar, each with its
evidence. Each excerpt must support the whole claim on its own; a heading,
label, or one-word cell is not evidence for anything it does not say. Never propose an `inferred` finding as a stated fact: either
propose it as an `open_question` citing the excerpt it was inferred from,
or list it in the handoff as not proposed. For meeting material, cite the
session note (not the raw transcript) as the primary `source_refs` entry,
and check decisions, open questions, stakeholders, action items, and risks
deliberately; meetings are the richest source for those five.

- **Action items** — propose every follow-up that has an owner or a stated
  need to assign one. Link the owner through `Owner Stakeholder IDs`,
  using a pending stakeholder's `proposal_id` if needed. Fill `Due Date`
  whenever the source gives a calendar date ("at the August 17
  onboarding"); keep relative timing such as "before kickoff" in the
  statement.
- **Risks** — propose each stated risk that clears the bar, carrying any
  mitigation the source gives.
- **Sessions** — propose one `session` row for every meeting processed,
  with `Status: completed`, `Scheduled Start` set to its date (left empty
  when the meeting is undated), and its session note as the source.

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

## Step 5 — Sync and hand off

Run this once, after the last batch. Run `PY <shared-skill-dir>/scripts/sync.py`. If validation produced one or more
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
- how many documents were processed and in how many batches, and whether
  curation fell back to running without subagents;
- the total number of evidence-backed items ready for their review, with
  counts by category;
- how many subagent candidates were dropped, grouped by reason, and any
  inferred findings that were not proposed;
- any documents filed without proposals and why, and any milestones whose
  date has passed with no source confirming the outcome;
- that these are proposed facts, not yet the project's official working
  record, and need their approval before they are added; and
- the exact next action in user language: for example, “I have 16 items
  ready for your approval. Would you like me to review and populate the
  project trackers now?”

If the user approves, invoke `workspace-review` and walk the
proposals through its governed review. If they do not approve, leave the
proposals in place and make clear that they are available for a later
review. Also report what was filed (including where any session note
lives).

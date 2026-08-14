---
name: review-updates
description: Walk the user through pending proposed updates in workspace/.system/proposed-updates/, show the evidence behind each one, let them approve, edit, or reject, and write the approved rows into the tracker workbooks. The only path that writes to the trackers.
---

# Review updates

Proposed updates only become tracker rows after a human approves them
here. Never apply updates the user has not seen.

Shorthand: `PY` = `.agents/skills/_shared/scripts/py`; engine scripts live
in `.agents/skills/_shared/scripts/`.

## Step 1 — What is pending

List `workspace/.system/proposed-updates/`. If it is empty, say so and
run `PY .agents/skills/_shared/scripts/sync.py --status` to show whether
any documents are waiting to be processed instead.

## Step 2 — Walk the updates

For each file, present the updates in small batches grouped by category.
For every update show:

- What it says (the key fields, in plain language)
- Where it came from — open the `source_refs` document and quote the
  supporting line(s)
- Whether it is an `add` or an `update` to an existing row (show the
  current row from `workspace/.system/tracker-copies/` for updates)

Let the user approve, edit, or reject each one. Apply their edits and
delete rejected updates directly in the YAML file. If the user says
"approve all", still scan for duplicates and obvious errors first and
flag anything suspicious before applying.

## Step 3 — Apply

For each file whose remaining updates are approved:

```
PY .agents/skills/_shared/scripts/validate_updates.py workspace/.system/proposed-updates/<file>.yaml
PY .agents/skills/_shared/scripts/apply_updates.py workspace/.system/proposed-updates/<file>.yaml
```

Fix validation problems before applying (usually enum values or link IDs).
`apply_updates.py` prints the assigned row IDs, moves the file to
`workspace/.system/applied-updates/`, and re-syncs automatically.

## Step 4 — Report

Tell the user what was written (IDs per category), what was rejected, and
anything worth following up — for example a pain point with no linked
stakeholder, or an open question nobody owns.

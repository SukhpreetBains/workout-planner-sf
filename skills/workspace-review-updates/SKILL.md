---
name: workspace-review-updates
description: Review pending evidence-backed updates in workspace/.system/proposed-updates/ with the user, let them approve, edit, or reject each change, and write only approved rows into workspace tracker workbooks. Use whenever proposed workspace updates await governed human review; this is the only workflow that writes to trackers.
---

# Review Workspace Updates

Proposed updates only become tracker rows after a human approves them
here. Never apply updates the user has not seen.

Locate `skills/_shared` alongside the installed skill library. Set
`EAD_REPO_ROOT` to the Opportunity folder for every engine command, then
run scripts through `_shared/scripts/py` or `_shared/scripts/py.cmd`.

## Visual review inbox

Start or reuse the loopback-only inbox with:

```
PY <shared-skill-dir>/scripts/review_server.py start --root "$EAD_REPO_ROOT"
```

Post the returned URL in chat and let the user open it. Never open the browser
automatically. The server assigns an ephemeral port, recovers from stale state,
and requires its session token for every mutation.

Each card is one proposal item, even when its source YAML contains several
updates. Edits autosave to pending YAML. Accept writes that one item to Excel,
syncs derived copies and the search index, and only then removes it from the
pending inbox. Reject archives the item without touching a tracker. Flag keeps
the item pending and adds the clarification note to
`workspace/.system/ai-review-queue.yaml`.

An active agent can wait for flags with:

```
PY <shared-skill-dir>/scripts/review_server.py wait --root "$EAD_REPO_ROOT" --timeout 60
```

If the returned `items` list is non-empty, resume the conversation with those
items. If review happens later, read `workspace/.system/ai-review-queue.yaml`
first on the user's next turn and work through unresolved flagged items before
the rest of the inbox.

## Step 1 — What is pending

List `workspace/.system/proposed-updates/`. If it is empty, say so and
run `PY <shared-skill-dir>/scripts/sync.py --status` to show whether
any documents are waiting to be processed instead.

Older pending files are upgraded in place the first time the inbox loads. The
upgrade adds stable proposal IDs, revision `1`, and source-reference evidence
entries without changing proposal fields.

## Step 2 — Walk the updates

When the visual inbox cannot run, fall back to presenting updates in small
batches grouped by category.
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
PY <shared-skill-dir>/scripts/validate_updates.py workspace/.system/proposed-updates/<file>.yaml
PY <shared-skill-dir>/scripts/apply_updates.py workspace/.system/proposed-updates/<file>.yaml
```

Fix validation problems before applying (usually enum values or link IDs).
`apply_updates.py` prints the assigned row IDs, moves the file to
`workspace/.system/applied-updates/`, and re-syncs automatically.

## Step 4 — Report

Tell the user what was written (IDs per category), what was rejected, and
anything worth following up — for example a pain point with no linked
stakeholder, or an open question nobody owns.

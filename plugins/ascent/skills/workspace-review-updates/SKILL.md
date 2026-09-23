---
name: workspace-review-updates
description: Review pending evidence-backed updates in workspace/.system/proposed-updates/ with the user, let them approve, edit, or reject each change, and write only approved rows into workspace tracker workbooks. Use whenever proposed workspace updates await governed human review; this is the only workflow that writes to trackers.
---

# Review Workspace Updates

Proposed updates only become tracker rows after a human approves them
here. Never apply updates the user has not seen.

Locate `shared/` at the installed Ascent plugin root. Set
`EAD_REPO_ROOT` to the Opportunity folder for every engine command, then
run scripts through `shared/scripts/py` or `shared/scripts/py.cmd`.
Use the Opportunity as the command working directory as well. Resolve the
installed plugin root explicitly; the scripts live under `shared/scripts/`,
not under this skill's directory. The launcher rejects missing or mismatched
roots before creating an environment. Do not retry a root error from the Account
folder or create an Account-level workspace.

Before anything else, confirm the workspace is initialized:

```
PY <plugin-root>/shared/scripts/sync.py --check-setup
```

This is a cheap, read-only filesystem check. If it reports the workspace as
not ready, stop here and tell the user this doesn't look like an initialized
Opportunity workspace, offer to hand off to `initial-setup` first.

## Visual review inbox

Start or reuse the loopback-only inbox with:

```
PY <plugin-root>/shared/scripts/review_server.py start --root "$EAD_REPO_ROOT"
```

Post the returned URL in chat and let the user open it. Never open the browser
automatically. The server assigns an ephemeral port, recovers from stale state,
and requires its session token for every mutation.

### Runtime permissions

A sandbox may deny localhost binding or health requests even when the workspace
is writable. When the host is known to block local sockets, launch with scoped
host access from the outset. Otherwise, if startup, status, wait, or stop reports
exit code 77, `PermissionError`, `Operation not permitted`, or a denied loopback
request, retry the same operation through the host's scoped permission mechanism
before choosing the chat fallback. In Codex, use `exec_command` with
`sandbox_permissions="require_escalated"` and a justification limited to the
local review server. Let the host approval mechanism decide; do not ask the user
to restate their request first. Do not disable sandboxing globally or broaden
the bind address beyond `127.0.0.1`.

A blocked health request does not prove that a server is stopped. Preserve its
state and retry with the same host access. Reuse that context for subsequent
server commands. If scoped access is denied or unavailable, explain the actual
block and continue the review in chat. If startup exits for another reason,
inspect the current log error before choosing a fallback.

Each card is one proposal item, even when its source YAML contains several
updates. Edits autosave to pending YAML. Accept writes that one item to Excel,
syncs derived copies and the search index, and only then removes it from the
pending inbox. Reject archives the item without touching a tracker. Flag keeps
the item pending and adds the clarification note to
`workspace/.system/ai-review-queue.yaml`.

An active agent can wait for flags with:

```
PY <plugin-root>/shared/scripts/review_server.py wait --root "$EAD_REPO_ROOT" --timeout 60
```

If the returned `items` list is non-empty, resume the conversation with those
items. If review happens later, read `workspace/.system/ai-review-queue.yaml`
first on the user's next turn and work through unresolved flagged items before
the rest of the inbox.

## Step 1, What is pending

List `workspace/.system/proposed-updates/`. If it is empty, say so and
run `PY <plugin-root>/shared/scripts/sync.py --status` to show whether
any documents are waiting to be processed instead.

Older pending files are upgraded in place the first time the inbox loads. The
upgrade adds stable proposal IDs, revision `1`, and source-reference evidence
entries without changing proposal fields.

## Step 2, Walk the updates

When the visual inbox cannot run, fall back to presenting updates in small
batches grouped by category.
For every update show:

- What it says (the key fields, in plain language)
- Where it came from, open the `source_refs` document and quote the
  supporting line(s)
- Whether it is an `add` or an `update` to an existing row (show the
  current row from `workspace/.system/tracker-copies/` for updates)

Let the user approve, edit, or reject each one. Apply their edits and
delete rejected updates directly in the YAML file. If the user says
"approve all", still scan for duplicates and obvious errors first and
flag anything suspicious before applying.

## Step 3, Apply

For each file whose remaining updates are approved:

```
PY <plugin-root>/shared/scripts/validate_updates.py workspace/.system/proposed-updates/<file>.yaml
PY <plugin-root>/shared/scripts/apply_updates.py workspace/.system/proposed-updates/<file>.yaml
```

Fix validation problems before applying (usually enum values or link IDs).
`apply_updates.py` prints the assigned row IDs, moves the file to
`workspace/.system/applied-updates/`, and re-syncs automatically.

## Step 4, Report

Tell the user what was written (IDs per category), what was rejected, and
anything worth following up, for example a pain point with no linked
stakeholder, or an open question nobody owns.

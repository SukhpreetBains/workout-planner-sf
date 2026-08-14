---
name: setup
description: First-time project onboarding. Prepares the Python environment, creates the tracker workbooks, captures project basics, files any starting documents from the inbox, extracts findings from them, and builds the search index. Run this once before any other workflow on a fresh clone.
---

# Setup

Get a fresh clone of this template ready for a real engagement. Everything
here is resumable — if a step already happened, skip it and move on.

Shorthand used below: `PY` = `.agents/skills/_shared/scripts/py`, and all
engine scripts live in `.agents/skills/_shared/scripts/`.

## Step 1 — Environment and trackers

Run:

```
PY .agents/skills/_shared/scripts/init_trackers.py
```

The first run creates `.venv/` and installs
`.agents/skills/_shared/requirements.txt`; it then
creates any missing tracker workbooks in `workspace/trackers/`. If Python
3.10+ is missing, stop and tell the user to install it first.

## Step 2 — Project basics

Ask the user, in plain English (partial answers are fine):

- Project name, client name, engagement type
- One-paragraph summary of what the engagement is about
- Key dates and the current focus

Write the answers to:

- `workspace/.system/project.yaml` — keys: `project`, `client`,
  `engagement_type`, `summary`, `dates`, `current_focus`
- `workspace/project/Project Overview.md` — the same content as readable
  prose (update the existing file, keep anything the user already wrote)

## Step 3 — File the starting documents

If `workspace/inbox/` has files, follow the **add-documents** skill
(`.agents/skills/add-documents/SKILL.md`) for the whole inbox: route each
file to the right workspace folder, record it in
`workspace/.system/sources.yaml`, and extract findings into proposed
updates. If the inbox is empty, say so and continue.

## Step 4 — Review and sync

- If extraction produced proposed updates, tell the user to run
  `/review-updates` to approve them — do not apply unreviewed updates
  yourself.
- Run `PY .agents/skills/_shared/scripts/sync.py` so the search index and
  tracker copies reflect whatever exists now.

## Step 5 — Summary

Tell the user, briefly: what was set up, how many documents were filed and
findings proposed, what is still missing (for example no stakeholder info
yet), and the next best action. The normal working loop from here on:

1. Drop new documents into `workspace/inbox/`
2. `/add-documents` (or `/add-meeting-notes` for a transcript)
3. `/review-updates` to approve what goes into the trackers
4. `/summarize` whenever a narrative picture is needed

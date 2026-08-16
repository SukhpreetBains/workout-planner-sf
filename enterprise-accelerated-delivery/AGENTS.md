# Agent Instructions

This repo turns client documents into structured, searchable project
knowledge. Documents arrive in `workspace/inbox/`, findings are proposed
as tracker updates, a human approves them in review, and approved rows
land in the Excel trackers in `workspace/trackers/`.

Operating rules:

- Workflows live in `.agents/skills/` — `setup`, `add-documents`,
  `add-meeting-notes`, `review-updates`, `summarize`. Load the relevant
  `SKILL.md` and follow it.
- The tracker schema (categories, columns, allowed values) is
  `.agents/skills/_shared/schema/trackers.yaml`. Never invent columns or
  enum values.
- Only `apply_updates.py` writes to the trackers, and only after the user
  approves the updates in `/review-updates`.
- Run engine scripts through `.agents/skills/_shared/scripts/py` (or
  `py.cmd` on Windows); it bootstraps `.venv` on first use.
- After changing workspace files or trackers by any other means, run
  `.agents/skills/_shared/scripts/py .agents/skills/_shared/scripts/sync.py`.
- To find things, prefer `search.py` and the plain-text tracker copies in
  `workspace/.system/tracker-copies/` over opening Excel files.

---
name: summarize-evidence
description: Produce an evidence-grounded narrative from an Opportunity workspace, such as a current-state picture, weekly rollup, topic deep-dive, or stakeholder view. Use when the user needs a summary from workspace documents and tracker rows; never modify trackers and keep any generated file inside workspace/.
---

# Summarize Evidence

Answer "what do we know?" in prose, grounded in tracker rows and filed
documents. This skill reads; it never writes to the trackers.

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

## Step 1 — Scope

Confirm what the user wants summarized (a topic, a time period, the whole
current state, a stakeholder or system) and where it should go: an answer
in chat, or a Markdown file in `workspace/current-state/` or
`workspace/future-state/`.

## Step 2 — Gather

- Run `PY <shared-skill-dir>/scripts/sync.py` first if documents were
  added since the last sync.
- Search across everything:
  `PY <shared-skill-dir>/scripts/search.py "<terms>"` (add
  `--kind pain_point` etc. to filter; `--id PAIN-003` for one full row).
- Read whole categories from `workspace/.system/tracker-copies/<category>.yaml`.
- Read the source documents behind the rows that matter — every tracker
  row's `Source Refs` column names its documents. Quote sources, not just
  tracker rows, for anything important.

## Step 3 — Write

Structure the summary around what the reader needs, not around the
tracker categories. Cite evidence inline as `(workspace/meetings/... )`
or `(PAIN-003)`. Be explicit about confidence: separate what multiple
sources agree on from what rests on a single mention, and call out
contradictions between sources rather than smoothing them over. End with
gaps — what we still do not know.

If writing to a file, name it plainly (for example
`workspace/current-state/Current State Summary.md`) and tell the user
where it is. Run `PY <shared-skill-dir>/scripts/sync.py` afterwards so
the new file is indexed.

# Project Workspace Setup

Initialize the standard workspace after the Opportunity path is confirmed and writable. The workflow is resumable: create missing state and preserve existing files and tracker rows.

Generated output artifacts, including decks, documents, and sites, belong in `workspace/deliverables/`. `Deliverables/` is reserved for a human to promote reviewed material into the appropriate delivery phase.

## 1. Locate the workspace engine

Locate `skills/_shared` alongside the installed skill library. Set `EAD_REPO_ROOT` to the Opportunity folder before invoking its `scripts/py` launcher so all generated state lands beneath `<Opportunity>/workspace/`.

On macOS or Linux:

```text
EAD_REPO_ROOT="<Opportunity folder>" <shared-skill-dir>/scripts/py <shared-skill-dir>/scripts/init_trackers.py
```

On Windows, set `EAD_REPO_ROOT` for the command session and use `scripts/py.cmd`.

The launcher creates `<Opportunity>/workspace/.system/.venv/` for runtime dependencies so generated project state remains inside `workspace/`.

## 2. Initialize trackers

Run `init_trackers.py`. It creates missing tracker workbooks and tabs without changing existing rows.

## 3. Record project basics

Use the Account and Opportunity already confirmed during setup. Ask only for missing details:

- engagement type
- a short engagement summary
- key dates
- current focus

Write:

```yaml
# workspace/.system/project.yaml
account: <account name>
opportunity: <opportunity name>
engagement_type: <type or null>
summary: <summary or null>
dates: <dates or null>
current_focus: <focus or null>
```

Update `workspace/project/Project Overview.md` with the same information in readable prose. Preserve useful existing content.

The project communications record remains `workspace/.system/source-context.yaml`; the ingested-document ledger remains `workspace/.system/sources.yaml`.

## 4. Process starting material

For a **new** Opportunity, ask the user: "Do you have any starting documents to add to `workspace/inbox/` now — SOWs, notes, transcripts, exports? Let me know when they're in place, or tell me to continue without them." Wait for their reply before re-checking the inbox; do not treat silence or a quick reply as "no documents" without confirming.

For an **existing** Opportunity, check `workspace/inbox/` once without prompting — documents may already be filed or waiting from prior sessions.

In both cases: if `workspace/inbox/` contains files, invoke `workspace-ingest-documents` — it handles both ordinary documents and meeting transcripts or raw notes. If the inbox is empty after this check, continue without treating it as an error — the user can add material at any later time and mention it to trigger the same skill.

Do not apply proposed updates. Direct the user to `workspace-review-updates` when review is needed.

## 5. Sync

Run `sync.py` through the same launcher and `EAD_REPO_ROOT` value. Report:

- trackers created or preserved
- documents filed
- proposed updates by category
- missing project basics
- search-index status
- the next best workflow by skill name

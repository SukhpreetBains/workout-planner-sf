# Project Workspace Setup

Initialize the standard workspace after the Opportunity path is confirmed and writable. The workflow is resumable: create missing state and preserve existing files and tracker rows.

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

If `workspace/inbox/` contains files, invoke `workspace-ingest-documents` for ordinary documents or `workspace-capture-meeting-notes` for a transcript or raw meeting notes. If the inbox is empty, continue without treating it as an error.

Do not apply proposed updates. Direct the user to `workspace-review-updates` when review is needed.

## 5. Sync

Run `sync.py` through the same launcher and `EAD_REPO_ROOT` value. Report:

- trackers created or preserved
- documents filed
- proposed updates by category
- missing project basics
- search-index status
- the next best workflow by skill name

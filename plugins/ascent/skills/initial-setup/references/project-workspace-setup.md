# Project Workspace Setup

Initialize the standard workspace after the Opportunity path is confirmed and writable. The workflow is resumable: create missing state and preserve existing files and tracker rows.

Generated output artifacts, including decks, documents, and sites, belong in `workspace/draft-deliverables/`. `Deliverables/` is reserved for a human to promote reviewed material into the appropriate delivery phase.

## 1. Locate the workspace engine

Locate `shared/` at the installed Ascent plugin root. Set `EAD_REPO_ROOT` to the Opportunity folder before invoking its `scripts/py` launcher so all generated state lands beneath `<Opportunity>/workspace/`.

On macOS or Linux:

```text
EAD_REPO_ROOT="<Opportunity folder>" <shared-skill-dir>/scripts/py <shared-skill-dir>/scripts/init_trackers.py
```

On Windows, set `EAD_REPO_ROOT` for the command session and use `scripts/py.cmd`.

The launcher creates `<Opportunity>/workspace/.system/.venv/` for runtime dependencies so generated project state remains inside `workspace/`.

## 2. Initialize trackers

Run `init_trackers.py`. It creates missing tracker workbooks and tabs without changing existing rows.

## 3. Record project identity

Use only the Account and Opportunity already confirmed during setup. Do not ask for engagement details, summaries, dates, focus areas, or other optional project context.

Reconcile `workspace/.system/project.yaml` instead of replacing it. Set the two identity keys below and preserve every other existing key and value:

```yaml
# workspace/.system/project.yaml
account: <account name>
opportunity: <opportunity name>
```

Update only the Account and Opportunity identity in `workspace/project/Project Overview.md`. Preserve all existing readable content, including optional project details that were recorded previously. Do not add blank placeholders for details setup no longer collects.

The project communications record remains `workspace/.system/source-context.yaml`; the ingested-document ledger remains `workspace/.system/sources.yaml`.

## 4. Leave source documents untouched

Do not inspect `workspace/inbox/`, ask about documents, or invoke a document-processing workflow during initial setup. Existing documents remain untouched.

At handoff, users with documents should open a fresh agent chat scoped to the Opportunity and request `workspace-ingest-documents`. Fresh context gives that agent maximum room to inspect, organize, extract, and reason over the source material. The plugin [workflow overview](../../../README.md) defines the lifecycle after setup.

## 5. Sync

Run `sync.py` through the same launcher and `EAD_REPO_ROOT` value. Report:

- trackers created or preserved
- Account and Opportunity identity recorded or preserved
- existing optional project details preserved
- search-index status
- the fresh-chat document next step and broader workflow guidance

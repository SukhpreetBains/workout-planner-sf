# Project Workspace Setup

Initialize the standard workspace after the Opportunity path is confirmed and writable. The workflow is resumable: create missing state and preserve existing files, identity fields, project details, and tracker rows.

Generated output artifacts belong in `workspace/draft-deliverables/`. `Deliverables/` is reserved for a human to promote reviewed material into the appropriate delivery phase.

## Run the orchestrated setup

Locate `shared/` and `initial-setup/` at the installed Ascent plugin root. Set `ASCENT_OPPORTUNITY_ROOT` to the confirmed Opportunity folder and invoke the setup script through the shared launcher:

```text
ASCENT_OPPORTUNITY_ROOT="<Opportunity folder>" <shared-dir>/scripts/py <initial-setup-dir>/scripts/setup-workspace.py --opportunity "<Opportunity folder>" --account "<account name>" --opportunity-name "<opportunity name>"
```

On Windows, set `ASCENT_OPPORTUNITY_ROOT` for the command session and use `<shared-dir>/scripts/py.cmd` with the same setup arguments.

Set `ASCENT_PYTHON` to the exact supported Python interpreter that should build or reuse the environment. Use `ASCENT_CACHE_DIR` only when the default per-user Ascent cache location must be overridden. Do not rely on the platform's ambiguous `python` or `python3` command selection.

The command runs the full sequence:

1. Resolve or create the per-user cached Python environment.
2. Write `workspace/.system/.venv-path` as a pointer to that environment. Do not place the environment inside the synced Opportunity folder.
3. Create or preserve the tracker workbooks and tabs.
4. Reconcile `workspace/.system/project.yaml` and `workspace/project/Project Overview.md` with the confirmed Account and Opportunity, preserving all other content.
5. Refresh the workspace search index.
6. Print the readiness report defined by [the setup readiness contract](setup-readiness.md).

The launcher must not silently install dependencies. If dependencies are missing, explain what is required and obtain approval before rerunning with `--install-dependencies`.

## Identity boundary

Use only the Account and Opportunity already confirmed during setup. Do not ask for engagement details, summaries, dates, focus areas, or optional project context.

The project communications record remains `workspace/.system/source-context.yaml`; the ingested-document ledger remains `workspace/.system/sources.yaml`.

## Record industry flavor, if applicable

After identity is recorded, follow **Confirm industry flavor** in
`SKILL.md`. When the user picks a pack (or explicitly declines), add one
more key to the same `project.yaml`, reconciled the same way:

```yaml
# workspace/.system/project.yaml
account: <account name>
opportunity: <opportunity name>
industry: <pack id, or the literal `none`>
```

This key is optional and only ever written after the user answers the
industry question — never inferred, and never added when no packs exist
to offer.

## Document boundary

Do not inspect `workspace/inbox/`, ask about documents, or invoke a document-processing workflow during setup. Existing documents remain untouched.

At handoff, follow [the setup readiness contract](setup-readiness.md). Users with documents should place them in the confirmed `<Opportunity folder>/workspace/inbox/` and open a fresh agent chat scoped to that Opportunity for `workspace-add`.

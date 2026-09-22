---
name: initial-setup
description: Bootstrap or resume an accelerated-delivery Opportunity workspace for a non-technical business user. Use when starting or joining a project, choosing shared or local-only storage, resolving a local sync, confirming project sources, creating the standard workspace and trackers, or recording Account and Opportunity identity.
---

# Initial Setup

Prepare one resumable Opportunity workspace. Preserve existing files, ask before system-level installs or source-record writes, and keep agent-created project work inside `workspace/`.

Use the host's structured-question tool when available. Ask one decision at a time and use plain language when structured questions are unavailable.

## Resources

- Run `scripts/bootstrap-environment.py` to verify Python 3.10+. Add `--include-node --install-missing` only when a selected workflow requires Node.js and npm and the user approves installation.
- Run `scripts/prepare-opportunity-folder.py` after the user chooses a new or existing Opportunity.
- Read [the storage decision tree](references/storage-decision-tree.md) when choosing or resolving storage. Read [the SharePoint walkthrough](references/sharepoint-walkthrough.md) only for its SharePoint branch.
- Read [messaging confirmation](references/messaging-confirmation.md) only when confirming Slack, Microsoft Teams, or the communications record. Read [Slack](references/slack.md), [Microsoft Teams](references/microsoft-teams.md), or [the source-context contract](references/source-context.md) only for the selected branch.
- Read [project workspace setup](references/project-workspace-setup.md) before initializing trackers, identity, and the search index.
- Use [setup readiness](references/setup-readiness.md) as the only checklist and status-definition source.
- Use the plugin [workflow overview](../../README.md) for workflow handoffs.

Explain a script's effect before running it. Obtain approval before package-manager installs or other system-level changes.

## Workflow

1. Verify Python 3.10+ and any workflow-specific dependencies.
2. Ask, **"Is there a shared workspace for this opportunity?"** Follow [the storage decision tree](references/storage-decision-tree.md), loading only the selected storage branch.
3. Ask whether the user is starting a new Opportunity or joining an existing one. Skip this question when a missing SharePoint Account folder was just created, because that path requires a new Opportunity.
4. Confirm the Account name, Opportunity name, local Account path, storage mode, applicable user-reported access, and local write readiness. Keep host sandbox limits separate from operating-system permissions.
5. Run a read-only folder preflight, then prepare the Account and Opportunity structure without overwriting existing files.
6. Invoke an applicable host project-setup workflow with the confirmed names and paths. If none applies, continue without loading host-specific guidance.
7. Follow [messaging confirmation](references/messaging-confirmation.md) for relevant enterprise storage and messaging locations. Offer to save confirmed locations in the project communications record.
8. Run the orchestrated workspace setup in [project workspace setup](references/project-workspace-setup.md). It initializes the runtime, trackers, identity, and search index.
9. Report readiness from [the authoritative readiness contract](references/setup-readiness.md), then hand document work to a fresh agent chat scoped to the Opportunity.

## Prepare the Opportunity folder

Confirm the local Account path, storage mode, Opportunity name, and new or existing mode before writing. Run the read-only preflight first:

```text
python3 scripts/prepare-opportunity-folder.py --mode <new|existing> --account-root <local-account-path> --opportunity-name <opportunity-name> --check-only
```

After confirmation, run the same command without `--check-only`. Both modes create missing standard folders and template files while preserving existing content. Generate the Account-level `AGENTS.md` from [the Account template](references/account-agent-workspace-template.md) only when missing. Keep agent work in `workspace/`; reserve `Deliverables/` for human promotion of reviewed material.

If the agent cannot write because of its session boundary, request scoped command access. Do not tell the user to change storage or folder permissions unless an operating-system check shows they are unavailable.

## Initialize project knowledge

Follow [project workspace setup](references/project-workspace-setup.md). Use the already confirmed `account` and `opportunity` values consistently. Never apply proposed tracker updates during setup. `workspace-review` remains the only workflow that writes approved tracker changes.

## Document boundary

Do not inspect `workspace/inbox/`, ask about documents, or process documents during setup. Leave existing documents untouched.

At handoff, tell users with documents to place documents, exports, meeting notes, transcripts, or other source files in the confirmed `<Opportunity folder>/workspace/inbox/`, then open a fresh agent chat scoped to the Opportunity. Include this prompt:

```text
Use workspace-add to process the documents in this Opportunity workspace inbox.
```

## Output contract

End with the compact **Setup readiness** report defined in [setup readiness](references/setup-readiness.md). Cover every required item under exactly one defined status group and give an actionable next step for anything incomplete.

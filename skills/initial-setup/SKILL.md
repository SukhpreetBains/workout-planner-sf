---
name: initial-setup
description: Bootstrap or resume an accelerated-delivery Opportunity workspace for a non-technical business user. Use when starting a new project or joining an existing project; verifying Python 3.10+; resolving SharePoint and OneDrive locations; confirming Slack or Microsoft Teams sources; creating the standard workspace and trackers; recording account and opportunity context; or processing the first project documents.
---

# Initial Setup

Prepare one resumable Opportunity workspace. Preserve existing files, ask before system-level installs or source-record writes, and keep agent-created project work inside `workspace/`.

## Use the bundled resources

- Run `scripts/bootstrap-environment.py --install-missing` to verify Python 3.10+. Add `--include-node` only when a selected workflow requires Node.js and npm.
- Run `scripts/prepare-opportunity-folder.py` after the user chooses a new or existing Opportunity.
- Use `scripts/manage-source-context.py` to manage the project communications record. Read [the source-context contract](references/source-context.md) before its first write.
- Read [project workspace setup](references/project-workspace-setup.md) before initializing trackers, project basics, starting documents, or the search index.
- Read [Slack](references/slack.md) or [Microsoft Teams](references/microsoft-teams.md) only when the user confirms that platform is relevant.

Explain a script's effect before running it. Obtain approval before package-manager installs or other system-level changes.

## Workflow

1. Verify Python 3.10+ and any workflow-specific dependencies.
2. Resolve the existing SharePoint Account folder and guide the user through its one-time OneDrive connection.
3. Ask whether the user is starting a new Opportunity or joining an existing one.
4. Confirm the local synced Account path, Account name, Opportunity name, user-reported SharePoint Edit access, and local write readiness.
5. Create or complete the standard `workspace/` and `Deliverables/` structure without overwriting existing files.
6. Confirm relevant SharePoint and messaging locations, then offer to save them in the project communications record.
7. Initialize the workspace environment, trackers, Account and Opportunity basics, and search index.
8. If starting documents exist in `workspace/inbox/`, invoke `workspace-ingest-documents`. Use `workspace-capture-meeting-notes` for transcripts or raw meeting notes.
9. Report setup readiness and direct the user to `workspace-review-updates` when proposed tracker changes exist.

## Verify the local environment

- Require Python 3.10 or newer.
- Treat Node.js and npm as optional. Check or install them only for a workflow that declares them as dependencies.
- Detect the operating system before suggesting package-manager commands.
- On macOS, prefer Homebrew when already available. On Windows, prefer `winget` when available.
- Rerun the environment check after any install attempt and report exactly what changed.
- If an unsupported or older Python runtime launches the script, stop and give the exact operating-system-specific next step.

## Resolve SharePoint and OneDrive

- Treat the existing customer-named Account folder as the source of truth. Do not recreate, rename, or move it.
- Use the SharePoint connector to resolve site, library, and folder metadata when available. Do not read SharePoint file contents during setup.
- Do not claim to have inspected SharePoint permissions. Ask the user to confirm Edit access and report that separately from local write readiness.
- Explain that the connector cannot establish OneDrive synchronization. Ask the user to select **Add shortcut to OneDrive**, or **Sync** on the containing library when needed.
- Continue only after the user identifies the locally synced Account path.
- Do not guess a synced path or use an ordinary downloaded copy as the working location.

## Prepare the Opportunity folder

Ask whether the user is starting a new Opportunity or joining an existing one. Confirm the Account path and Opportunity name before writing.

Run a read-only preflight first:

```text
python3 scripts/prepare-opportunity-folder.py --mode <new|existing> --account-root <synced-account-path> --opportunity-name <opportunity-name> --check-only
```

After confirmation, run the same command without `--check-only`. Both modes safely create missing standard folders and template files while preserving everything already present.

The resulting structure is:

```text
<Account folder>/
  <Opportunity name>/
    AGENTS.md
    workspace/
      inbox/
      project/
      meetings/
      current-state/
      future-state/
      reference/
      trackers/
      .system/
    Deliverables/
      Mobilize/
      Discover/
      Deliver/
      Transition/
```

Keep agent-created project files, working documents, trackers, indexes, and source records inside `workspace/`. Do not write agent work into `Deliverables/`.

## Confirm messaging sources

- Ask whether Slack and Microsoft Teams contain relevant project conversations. Treat them as defaults only after the user confirms them.
- Request one known channel, team/channel, or distinctive Account or workstream term for each confirmed platform, then follow its reference workflow.
- Treat a successful connector response as authentication, not proof of usable project access. Mark a platform usable only after the expected source is returned.
- Report no-match results as **scope not verified**. Do not infer that a channel does not exist.
- Do not read messages, files, or threads unless the platform reference explicitly permits a consented fallback.
- Do not create, rename, or modify messaging channels during setup.

## Maintain the project communications record

Use `<Opportunity folder>/workspace/.system/source-context.yaml` as the project-owned record of confirmed SharePoint, messaging, and other external project locations.

- Keep `account`, `opportunity`, and `last_verified` at the top level.
- Store external source locations and access state only. Never store message text, document contents, credentials, OAuth data, or permission payloads.
- Save only locations confirmed by the user. Keep candidates and exclusions in the conversational setup report.
- Ask before the first write: "Would you like me to save these confirmed project locations so they are easy to find next time?"
- Reconcile an existing record instead of replacing it. Preserve unknown fields and mark unavailable prior sources as `scope_not_verified` rather than deleting them.
- Treat `workspace/.system/sources.yaml` as a separate ledger of individual documents ingested into the workspace.

## Initialize project knowledge

Follow [project workspace setup](references/project-workspace-setup.md). Use `account` and `opportunity` consistently in machine-readable project data. Do not ask for identity values already confirmed during Opportunity setup.

Never apply proposed tracker updates during setup. `workspace-review-updates` remains the only workflow that writes approved changes into trackers.

## Output

End with a compact **Setup readiness** checklist in this order:

```text
✅ Completed automatically
🔎 Verified — user action still needed
⚠️ Blocked or limited by connector/runtime
```

Cover Python, OneDrive and Opportunity path, workspace structure, SharePoint, messaging sources, project communications record, trackers, starting documents, and search index. Give one concise next step whenever anything remains incomplete.

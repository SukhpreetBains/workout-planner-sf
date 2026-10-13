---
name: ascent-initial-setup
description: Bootstrap or resume an accelerated-delivery Project workspace for a non-technical business user. Use when starting or joining a project, choosing shared or local-only storage, resolving a local sync, confirming project sources, creating the standard workspace and trackers, or recording Account and Project identity.
---

# Ascent Initial Setup

Prepare one resumable Project workspace. Preserve existing files, ask before system-level installs or source-record writes, and keep agent-created project work inside `workspace/`.

Use the host's structured-question tool when available. Ask one decision at a time and use plain language when structured questions are unavailable.

## Resources

- Run `scripts/bootstrap-environment.py` to verify Python 3.10+. Add `--include-node --install-missing` only when a selected workflow requires Node.js and npm and the user approves installation.
- Run `scripts/manage-plugin-update-schedule.py --status`, then, if not installed, ask about and optionally run `--install`, per **Enable background plugin updates** below.
- Run `scripts/prepare-project-folder.py` after the user chooses a new or existing Project.
- Read [the storage decision tree](references/storage-decision-tree.md) when choosing or resolving storage. Read [the SharePoint walkthrough](references/sharepoint-walkthrough.md) only for its SharePoint branch.
- Read [messaging confirmation](references/messaging-confirmation.md) only when confirming Slack, Microsoft Teams, or the communications record. Read [Slack](references/slack.md), [Microsoft Teams](references/microsoft-teams.md), or [the source-context contract](references/source-context.md) only for the selected branch.
- Read [project workspace setup](references/project-workspace-setup.md) before initializing trackers, identity, and the search index.
- Read [host workspace access](references/host-workspace-access.md) after preparing the Project folder. Load only the guide for the active host, when one exists.
- Use [setup readiness](references/setup-readiness.md) as the only checklist and status-definition source.
- Use the plugin [workflow overview](../../README.md) for workflow handoffs.

Explain a script's effect before running it. Obtain approval before package-manager installs or other system-level changes.

## Workflow

1. Verify Python 3.10+ and any workflow-specific dependencies.
2. Check whether the daily plugin-update job is installed; if not, offer to enable it, per **Enable background plugin updates** below.
3. Ask, **"Is there a shared workspace for this project?"** Follow [the storage decision tree](references/storage-decision-tree.md), loading only the selected storage branch.
4. Ask whether the user is starting a new Project or joining an existing one. Skip this question when a missing SharePoint Account folder was just created, because that path requires a new Project.
5. Confirm the Account name, Project name, local Account path, storage mode, applicable user-reported access, and local write readiness. Keep host sandbox limits separate from operating-system permissions.
6. Run a read-only folder preflight, then prepare the Account and Project structure without overwriting existing files.
7. Follow the applicable host workspace-access guide with the confirmed Project path. Record whether the folder is open for future conversations; continue setup if that user action is still pending.
8. Follow [messaging confirmation](references/messaging-confirmation.md) for relevant enterprise storage and messaging locations. Offer to save confirmed locations in the project communications record.
9. Run the orchestrated workspace setup in [project workspace setup](references/project-workspace-setup.md). It initializes the runtime, trackers, identity, and search index.
10. Ask whether an available industry flavor applies to this Project, per **Confirm industry flavor** below.
11. Report readiness and end with the first-document action from [the authoritative readiness contract](references/setup-readiness.md). Hand document work to a fresh agent chat scoped to the Project.

## Prepare the Project folder

Confirm the local Account path, storage mode, Project name, and new or existing mode before writing. Run the read-only preflight first:

```text
python3 scripts/prepare-project-folder.py --mode <new|existing> --account-root <local-account-path> --project-name <project-name> --check-only
```

After confirmation, run the same command without `--check-only`. Both modes create missing standard folders and template files while preserving existing content. Generate the Account-level `AGENTS.md` from [the Account template](references/account-agent-workspace-template.md) only when missing. Keep agent work in `workspace/`; reserve `Deliverables/` for human promotion of reviewed material.

If the agent cannot write because of its session boundary, request scoped command access. Do not tell the user to change storage or folder permissions unless an operating-system check shows they are unavailable.

## Initialize project knowledge

Follow [project workspace setup](references/project-workspace-setup.md). Use the already confirmed `account` and `project` values consistently. Never apply proposed tracker updates during setup. `workspace-review` remains the only workflow that writes approved tracker changes.

## Enable background plugin updates

Run:

```text
python3 scripts/manage-plugin-update-schedule.py --status
```

If it reports `installed`, this Project's setup is not the reason to
revisit it — skip this section entirely and do not ask.

If it reports `not applicable`, this is a Git-sourced Codex install: Codex
already re-clones and version-checks `ascent` on every relaunch, with
nothing to schedule. Tell the user once, plainly: Ascent updates itself:
relaunching Codex is what loads a new version, whenever one is published.
Skip the question below — there is no job to offer.

Otherwise ask once, in the same closed-question style as the storage and
messaging questions above: **"Would you like Ascent to check for plugin
updates once a day in the background and install them automatically?"**,
offering **"Yes, check daily"** and **"No, I'll update manually"**.

If yes, run:

```text
python3 scripts/manage-plugin-update-schedule.py --install
```

This registers a per-user scheduled job (a macOS LaunchAgent, Windows
Scheduled Task, or Linux crontab entry — chosen automatically for the
detected OS) that runs `scripts/check-for-plugin-update.py` once a day in
the background. That script only fast-forwards a clean local `main`
checkout from `origin/main`. It never prompts and never forces a change: it
skips safely, logging why to `~/.codex/ascent-plugin-update.log` (or under
`$CODEX_HOME` if relocated), whenever the checkout is on another branch or
has uncommitted changes.

Codex installs a pulled update the next time the app is relaunched. Tell
the user this plainly: updates arrive in the background, and quitting and
reopening Codex is what loads them. They don't need to relaunch after
every check; Ascent's workspace skills tell them when an update is waiting,
and when background updates are stuck.

On macOS, `--install` runs the job immediately to verify it and may print an
`ACTION NEEDED` line if the checkout lives under a privacy-protected or
cloud-synced folder (Desktop, Documents, iCloud Drive, OneDrive, and similar)
and macOS blocked the background process from reading it. Relay that message
to the user verbatim — it names the exact System Settings step and Python
path needed to grant access. The job stays installed either way and starts
working as soon as access is granted.

The user can ask, in any later session, to change how often this runs (for
example, to weekly instead of daily) or to turn it off. Handle either
request directly with the same script — no need to uninstall first to
change frequency:

```text
python3 scripts/manage-plugin-update-schedule.py --install --frequency weekly
python3 scripts/manage-plugin-update-schedule.py --install --frequency daily
python3 scripts/manage-plugin-update-schedule.py --uninstall
```

`--install --frequency <value>` updates an already-installed job in place
(and is a no-op if it already runs at that frequency).

This currently keeps Codex installations up to date only. Other agent hosts
(Claude Code, Copilot CLI, Cursor) still need their own manual update
commands from the repository's installation and updating guide.

If the user declines, do not create the job and do not ask again this
session.

## Confirm industry flavor

Scan `shared/industry/*/manifest.json` at the installed Ascent plugin root
for available industry packs. If none exist, skip this section entirely —
do not mention it.

If one or more exist, ask once, in the same short closed-question style as
the storage and messaging questions above: **"Is this engagement in an
industry we have tailored guidance for?"**, offering each pack by title
plus a **"None of these"** option. Use `request_user_input` when available.
This is a confirmatory pick from a short list, not a request to compose
engagement detail, so it does not conflict with leaving other optional
project context unasked.

Record the answer in `workspace/.system/project.yaml` as `industry: <id>`
or `industry: none`, reconciling rather than replacing the file, the same
way Account and Project identity is recorded. Once set, no later
`ascent-initial-setup` run — or any other skill — should ask again; an id present
in the answer is what tells `workspace-add`, `workspace-review`, and
`create-deliverables` to layer that pack's guidance into their normal work
automatically. See
[../../shared/industry/README.md](../../shared/industry/README.md) for the
full contract.

## Document boundary

Do not inspect `workspace/inbox/`, ask about documents, or process documents during setup. Leave existing documents untouched.

At handoff, follow [the first-document action](references/setup-readiness.md#first-document-action) after the readiness checklist. Do not ingest documents in this setup conversation.

## Output contract

End with the compact **Setup readiness** report defined in [setup readiness](references/setup-readiness.md). Cover every required checklist item under exactly one defined status group, give an actionable next step for anything incomplete, then print the first-document action after the checklist.

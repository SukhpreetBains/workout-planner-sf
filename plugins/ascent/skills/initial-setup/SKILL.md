---
name: initial-setup
description: Bootstrap or resume an accelerated-delivery Opportunity workspace for a non-technical business user. Use when starting a new project or joining an existing project; choosing shared or local-only storage; resolving an enterprise storage location and its local sync; verifying Python 3.10+; guiding Codex project creation; confirming Slack or Microsoft Teams sources; creating the standard workspace and trackers; recording account and opportunity context; or processing the first project documents.
---

# Initial Setup

Prepare one resumable Opportunity workspace. Preserve existing files, ask before system-level installs or source-record writes, and keep agent-created project work inside `workspace/`.

## Use the bundled resources

- Run `scripts/bootstrap-environment.py --install-missing` to verify Python 3.10+. Add `--include-node` only when a selected workflow requires Node.js and npm.
- Run `scripts/prepare-opportunity-folder.py` after the user chooses a new or existing Opportunity.
- Use `scripts/manage-source-context.py` to manage the project communications record. Read [the source-context contract](references/source-context.md) before its first write.
- Read [project workspace setup](references/project-workspace-setup.md) before initializing trackers, project basics, starting documents, or the search index.
- Read [Slack](references/slack.md) or [Microsoft Teams](references/microsoft-teams.md) only when the user confirms that platform is relevant.
- Invoke `project-setup` only after the local Opportunity folder and its exact Account and Opportunity names are confirmed and the user says they use Codex.

Explain a script's effect before running it. Obtain approval before package-manager installs or other system-level changes.

## Workflow

1. Verify Python 3.10+ and any workflow-specific dependencies.
2. Ask, **"Is there a shared workspace for this opportunity?"** and follow the storage decision flow below.
3. Ask whether the user is starting a new Opportunity or joining an existing one.
4. Confirm the local working Account path, Account name, Opportunity name, applicable user-reported storage access, and local write readiness. Keep a runtime sandbox boundary separate from local write readiness: if the agent cannot write because of its session boundary, say so and request scoped command access; do not imply the user must change storage or folder permissions unless an operating-system check shows that they are unavailable.
5. Create or complete the standard `workspace/` and `Deliverables/` structure without overwriting existing files.
6. Ask whether the user uses Codex for this Opportunity. If yes, invoke `project-setup` with the confirmed Account and Opportunity names and paths. After asking whether the Codex project was created, continue setup regardless of the answer.
7. Confirm relevant enterprise storage and messaging locations, then offer to save them in the project communications record.
8. Initialize the workspace environment, trackers, Account and Opportunity basics, and search index.
9. For a new Opportunity, pause and ask whether the user has starting documents to add to `workspace/inbox/` now, then wait for their response before re-checking the inbox. For an existing Opportunity, check `workspace/inbox/` once without prompting. If files are present, including files copied from a confirmed external source, report what is staged. Unless the user has already requested this work, use plain language rather than the internal term "ingestion": explain that the next step will organize the documents into the project folders, pull out key facts, and prepare suggested tracker updates for the user to review. State that source documents stay intact and trackers will not change without the user’s approval, then ask whether to do that now. After the user consents, invoke `workspace-ingest-documents`.
10. Report setup readiness and direct the user to `workspace-review-updates` when proposed tracker changes exist.

## Verify the local environment

- Require Python 3.10 or newer.
- Treat Node.js and npm as optional. Check or install them only for a workflow that declares them as dependencies.
- Detect the operating system before suggesting package-manager commands.
- On macOS, prefer Homebrew when already available. On Windows, prefer `winget` when available.
- Rerun the environment check after any install attempt and report exactly what changed.
- If an unsupported or older Python runtime launches the script, stop and give the exact operating-system-specific next step.

## Choose shared or local-only storage

Ask the storage questions one at a time and follow only the branch selected by the user.

Use the default-mode `request_user_input` tool for storage and setup questions with known choices whenever it is available. Present short, mutually exclusive options in the tool instead of typing a plain-text question. Ask one decision at a time so the user sees only choices relevant to the selected branch. If the tool is unavailable, ask the same question directly in plain language.

### No shared workspace exists

Ask, **"Would you like help setting up a shared workspace or would you prefer to set it up so it's only on your computer?"**

- If they choose a shared workspace, ask, **"Are you using SharePoint for file storage or another cloud storage solution?"** Route SharePoint and other enterprise storage as described below.
- If they choose **Only on my computer**, offer to place the Account folder on their Desktop or let them provide another parent folder. Confirm the Account name, Opportunity name, and full proposed path before creating anything. Inspect the resolved parent path first and tell the user if a Desktop or parent folder is already redirected into cloud storage. Create or reuse `<chosen parent>/<Account name>` as the Account root, then prepare the Opportunity structure there. Make clear that this local-only workspace will not be shared or synchronized automatically.

### A shared workspace exists

Ask, **"In order to work in that space we need to get it synced locally on your machine. Would you like help getting it synced locally?"**

- If they want help, ask, **"Are you using SharePoint for file storage or another cloud storage solution?"** Route the answer as described below.
- If they decline help, do not assume a synced path is available. Offer to create a separate local-only workspace using the Desktop-or-user-provided-folder flow. Explain that work in that folder will not automatically appear in the existing shared workspace.

### SharePoint

- Send this message, preserving the linked text:

  > Here is a link to the [Ascent Account Folder](https://twodegrees1.sharepoint.com/teams/Ascent/Shared%20Documents/Forms/AllItems.aspx?id=%2Fteams%2FAscent%2FShared%20Documents%2FAccounts&viewid=0a588853%2D4cd8%2D489c%2Db39e%2Dd322bfb46652). Look to see if the account already exists.

- Ask, **"Did you find a folder for the account you are working on?"** Use `request_user_input` when available, with short options for **Yes, I found it** and **No, it is missing**.
- If the Account folder does not exist, send these steps:

  > 1. Click the **+ Create or upload** button.
  > 2. Select **Folder**.
  > 3. Type the name of the Account in the **Name** field.
  > 4. Click the **Create** button.

  Immediately below the creation steps, display these images in order:
  1. [The Create or upload example](assets/sharepoint-create-or-upload.png), with alt text identifying the highlighted **+ Create or upload** button.
  2. [The Folder option example](assets/sharepoint-select-folder.png), with alt text identifying the highlighted **Folder** option.
  3. [The Create a folder example](assets/sharepoint-create-account-folder.png), with alt text identifying the **Name** field and highlighted **Create** button.

  Resolve all three assets to their absolute filesystem paths in the rendered response. After showing the folder-creation guidance, continue directly to the shortcut steps below.
- If the Account folder exists, or after showing how to create it, send these shortcut steps:

  > 1. Navigate to the Account folder by clicking on it.
  > 2. Click the **Add shortcut to OneDrive** button.
  > 3. Select **My files** from the menu that opens.

  Immediately below the shortcut steps, display both images in this order:
  1. [The SharePoint shortcut example](assets/sharepoint-add-shortcut-to-onedrive.png), with alt text identifying the highlighted **Add shortcut to OneDrive** button.
  2. [The My files example](assets/sharepoint-select-my-files.png), with alt text identifying the highlighted **My files** option.

  Resolve both assets to their absolute filesystem paths in the rendered response so the images display in the app.
- After the two images, say:

  > Once you have clicked on "My Files" let me know the name of the account and I will go look for the local connection to that folder you just created

- Stop and wait for the account name. Do not append a request for the locally synced path or Edit-access confirmation to this message.
- After the user provides the Account name, inspect the standard local OneDrive sync locations. Search first for the likely shortcut folder name `Ascent - <Account name>`, then check `<Account name>` as a fallback. Compare names case-insensitively, but do not use partial matches. Resolve candidate paths before presenting them. If exactly one valid local connection exists, report it and continue. If no exact match is found, explain that the shortcut may still be syncing and that the local folder might not be discoverable immediately. Offer to retry, and give a path-copy fallback: in Finder, select the Account folder, hold **Option**, right-click, choose **Copy "<Account name>" as Pathname**, and paste the copied path into the conversation. If multiple matches exist, explain what was found and use `request_user_input` when available to obtain the needed choice. Do not guess the path.
- Treat the existing customer-named Account folder as the source of truth. Do not recreate, rename, or move it.
- Use the SharePoint connector to resolve site, library, and folder metadata when available. Do not read SharePoint file contents during setup.
- Do not claim to have inspected SharePoint permissions. Confirm Edit access separately later in setup, after resolving the local Account path.
- Explain that the connector cannot establish OneDrive synchronization, which is why the user must add the shortcut through SharePoint.
- Continue only after resolving and confirming the locally synced Account path.
- Do not guess a synced path or use an ordinary downloaded copy as the working location.

### Other enterprise storage

Ask, **"What enterprise storage solution are you using?"** Then:

1. Check whether an installed plugin can access that provider. If none is installed, use the host's plugin discovery mechanism when available and offer the exact relevant plugin to the user. Install or connect it only with the user's authorization.
2. Treat provider access through a plugin as separate from desktop synchronization. Use the plugin to help resolve or verify the shared location when supported, but still obtain a confirmed locally synced path before workspace setup.
3. If no suitable plugin exists, ask for consent before researching the provider. Use authoritative provider documentation to guide installation or configuration of its desktop sync client when local synchronization is supported.
4. Do not guess a synced path or treat an ordinary downloaded copy as synchronized storage. Confirm the local path and write readiness.
5. If the provider cannot be connected or synced locally, state that this setup cannot use it as a shared workspace. Offer the Desktop-or-user-provided-folder local-only flow instead and explain that it will not synchronize automatically.

## Prepare the Opportunity folder

Ask whether the user is starting a new Opportunity or joining an existing one. Confirm the local Account path, storage mode, and Opportunity name before writing.

Run a read-only preflight first:

```text
python3 scripts/prepare-opportunity-folder.py --mode <new|existing> --account-root <local-account-path> --opportunity-name <opportunity-name> --check-only
```

After confirmation, run the same command without `--check-only`. Both modes safely create missing standard folders and template files while preserving everything already present.

The resulting structure is:

```text
<Account folder>/
  <Opportunity name>/
    AGENTS.md
    workspace/
      inbox/
      draft-deliverables/
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

Keep agent-created project files, working documents, trackers, indexes, and source records inside `workspace/`. Store generated output artifacts such as decks, documents, and sites in `workspace/draft-deliverables/`. Do not write agent work into `Deliverables/`; that folder is reserved for human promotion of reviewed material into a delivery phase.

## Offer Codex project setup

After the Opportunity folder exists locally and the standard structure is
ready, ask, **"Are you using Codex for this Opportunity?"** Use
`request_user_input` when it is available, with short choices for **Yes, using
Codex** and **No, continue setup**.

- If the user says yes, invoke `project-setup` and pass the confirmed Account
  name, Opportunity name, local Account path, and local Opportunity path. Let
  that skill show the user-controlled project-creation steps.
- When `project-setup` asks whether the project was created, record the answer
  but continue this workflow whether the answer is yes, no, dismissed, or
  otherwise unverified.
- If the user says no, continue directly to messaging-source confirmation.
- Do not create a Codex project through browser automation or by editing Codex
  global state during initial setup.

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
🔎 Verified, user action still needed
⚠️ Blocked or limited by connector/runtime
```

Cover Python, storage mode and local Opportunity path, workspace structure, applicable shared storage, applicable Codex project status, messaging sources, project communications record, trackers, starting documents, and search index. Give one concise next step whenever anything remains incomplete.

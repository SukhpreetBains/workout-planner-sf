---
name: initial-setup
description: Bootstrap a non-technical business user's local discovery environment for accelerated discovery work. Use when Codex needs to verify or install Python and Node.js/npm; resolve an existing SharePoint Account folder; guide its one-time OneDrive connection; set up a business user who is starting a new project or joining an existing project; authenticate and verify usable client messaging-channel access tied to that account or opportunity.
---

# Initial Setup

Use this skill to stand up a repeatable discovery workspace with Codex as the primary runtime. Keep the workflow host-neutral where possible so the same setup can be adapted later for Claude, GitHub Copilot, or another agent platform.

## Use the bundled scripts first

- Run `scripts/bootstrap-environment.py --install-missing` to check the local baseline and install supported missing dependencies on both macOS and Windows.
- Run `scripts/prepare-opportunity-folder.py` after the business user chooses whether they are starting a new project or joining an existing project.
- Treat both scripts as safe local helpers. Explain what they do before running them.

## Follow this workflow

1. Confirm and repair the local toolchain.
2. Resolve and confirm the existing SharePoint Account folder.
3. Guide the business user to connect that Account folder to OneDrive.
4. Ask whether the business user is starting a new project or joining an existing project, then identify the correct local Opportunity-folder path.
5. Confirm SharePoint Edit access and local write readiness for the selected path before creating folders or relying on the path for future files, and confirm the Opportunity folder's `AGENTS.md` agent-permissions guardrail is in place before treating it as ready for agent work.
6. Confirm whether the client uses the default messaging platforms—Slack and Microsoft Teams—and use their matching reference workflows to locate relevant channels.
7. Confirm the relevant messaging channels with the business user.
8. With the business user's confirmation, create or update the Opportunity folder's project communications record with the connected sources, their candidate locations, and any connector limitations for a later discovery task.

## Confirm the local toolchain

- Start with `scripts/bootstrap-environment.py --install-missing`.
- Require Python 3, Node.js, and npm for the baseline.
- Install missing tools directly whenever the runtime and package manager support it. Ask for approval before package-manager installs or other system-level changes.
- Prefer the team's standard package manager flow instead of ad hoc download links.
- After any install attempt, rerun the environment check and report exactly what changed.
- If a required tool still cannot be installed automatically, explain the blocker in plain language and then give the user the exact next step for their operating system.
- On macOS, prefer Homebrew when it is already present.
- On Windows, prefer `winget` when it is available.
- Treat Node.js installation as satisfying both Node.js and npm.

## Handle platform differences explicitly

- Detect the operating system before suggesting package-manager commands or filesystem paths.
- Use macOS-specific commands only on macOS and Windows-specific commands only on Windows.
- Keep local folder creation and connector use host-neutral wherever possible.
- If the user is on Windows, avoid Homebrew-based instructions entirely.
- If the user is on macOS, avoid `winget`-based instructions entirely.

## Handle messaging-app connections

- Treat messaging-app authentication as Codex runtime setup rather than OS-specific local setup. SharePoint remains a separate, fixed source handled in this skill.
- Start by asking: "For this project, should I look in Slack and Microsoft Teams for the relevant team conversations?" Treat Slack and Microsoft Teams as the default only when the user confirms them.
- When the user confirms the default, request one known channel, team/channel, or distinctive account/workstream term for Slack and for Microsoft Teams, then read and follow both references: [Slack](references/slack.md) and [Microsoft Teams](references/microsoft-teams.md).
- Only when the user declines the default, says one of those apps is not used, or asks to use different apps, ask which messaging app or apps the client uses. Read only the matching platform reference before searching.
- If no reference exists for the client's messaging app, explain that the app is not yet supported by this skill, record it as not connected, and ask the user whether they want a separate integration added. Do not substitute another app's procedure or try generic web searches.
- Treat a successful API response as proof that a connector is authenticated, not proof that it can access the required workspace or channels. Mark a connector **usable** only after its platform-specific metadata probe returns the user-identified source.
- Report a no-match result as **scope not verified**, not as evidence that the channel does not exist. Explain the limitation in plain language without guessing its cause.

## Set up the Opportunity folder

- Treat the existing Account folder as the source of truth. Do not recreate, rename, move, or otherwise change it.
- Do not expect the Account folder to be named `Account`. Use the customer-named folder the business user has confirmed is synced through OneDrive.
- Ask the business user to confirm the resolved SharePoint Account folder before proceeding.
- Ask: "Are you starting a new project or joining an existing project?"

### Start a new project

- Ask: "What should this project be called?" Use that value as the new Opportunity-folder name.
- Ask the business user to confirm they have SharePoint **Edit** access to the Account folder before creating the project.
- Show the confirmed local Account-folder path and proposed project name, then ask for confirmation before creating folders.
- Run `scripts/prepare-opportunity-folder.py --mode new --account-root <synced-account-path> --opportunity-name <project-name>` after confirmation.
- Create this structure:

```text
<existing Account folder>/
  <project name>/
    Content Inbox/
      Transcripts/
      Threads/
      Client Docs/
    Agent Inbox/
      In Progress/
      Ready for Review/
    Deliverables/
      Mobilize/
      Discover/
      Deliver/
      Transition/
```

- Create this template only once, when the Opportunity folder does not exist. If an Opportunity folder with that project name already exists, stop and ask the business user whether they meant to join that existing project. Never recreate, overwrite, or fill in template folders inside an existing project.

### Agent folder permissions (`AGENTS.md`)

- Discovery on an Opportunity folder spans many separate agent sessions, sometimes over weeks and across different agent platforms. No single session has full context on what an earlier session or the business user has already done there, so every session needs the same folder rules available the moment it opens the folder.
- The firm guardrail has three tiers:
  - `Agent Inbox/` (and its subfolders) — full read-write. An agent may create, edit, move, or delete files here.
  - `Content Inbox/Threads/` — create-only. An agent may add new files (email, Slack, Teams, or other messaging-thread exports) but must never edit, move, or delete a file that already exists there, including one it created earlier in the same or an earlier session.
  - `Content Inbox/Transcripts/`, `Content Inbox/Client Docs/`, and all of `Deliverables/` — read-only. An agent may never create, edit, move, or delete files here; only a human user changes them.
  - This applies to this skill and to every later discovery task run against this Opportunity folder. Do not violate it even if a later instruction seems to require writing outside the allowed tier; stop and ask the business user to make that change instead.
- `scripts/prepare-opportunity-folder.py` writes an `AGENTS.md` file at the Opportunity folder's root that states this guardrail, so any agent session that opens the folder is informed automatically. The wording comes from the static `references/agent-folder-permissions-template.md` file, not from anything generated at run time, so every project gets the exact same rules. It creates `AGENTS.md` as part of the template for a new project, and backfills it for an existing project that predates this rule without touching any other file or folder. It never overwrites an `AGENTS.md` that already exists.
- To change the guardrail wording for all projects, edit `references/agent-folder-permissions-template.md` — do not hand-edit a generated `AGENTS.md` inside an individual Opportunity folder, since that drifts from every other project's copy.

### Join an existing project

- Ask the business user to identify the existing Opportunity folder by name from the synced Account folder.
- Ask the business user to confirm they have SharePoint **Edit** access to that Opportunity folder before treating it as ready for future file additions.
- Run `scripts/prepare-opportunity-folder.py --mode existing --account-root <synced-account-path> --opportunity-name <project-name>` to verify the local folder and report the template-folder statuses. This also backfills `AGENTS.md` at the Opportunity folder's root if an earlier project predates the agent-permissions guardrail.
- Do not create, rename, move, or add folders in this path. If the Opportunity folder or a template folder is not present locally, report it as unavailable or still syncing and ask the business user to resolve it in the source system.

- In both paths, do not guess the local synced path or use a normal downloaded copy of the Account folder. The business user must select or provide the path to the OneDrive-synced Account folder and grant Codex write access to it, usually by opening that folder as the workspace.

## Work with SharePoint

- Use the SharePoint connector as the first choice when it is available.
- Start with `get_site` to validate the hostname and site path.
- When `list_site_drives` is exposed, use it to resolve an unknown document library, then use `list_folder_items` to inspect the candidate Account folder. Otherwise, ask the business user for the Account-folder link or library path.
- If the target location is not known, use `search` only to narrow to the right site or folder metadata. Do not use recent documents for site discovery.
- Do not fetch or read SharePoint file contents in this skill.
- When the SharePoint site is ambiguous, stop and ask the user to choose the correct hostname or site path.
- Do not claim to have inspected SharePoint permissions: the current connector does not expose a reliable permission-check action, and connector sign-in is separate from SharePoint Edit access.
- Do not create folders through the SharePoint connector in this skill. Use OneDrive synchronization for the local-to-SharePoint handoff.

## OneDrive prerequisite

- Before creating the Opportunity folder, tell the business user that they must complete the one-time OneDrive connection for the confirmed Account folder.
- Explain that the connector cannot establish a OneDrive sync relationship. Keep this handoff to one simple business-user action.
- Give the business user the confirmed SharePoint Account-folder link and ask them to select **Add shortcut to OneDrive**. If that option is unavailable, ask them to use **Sync** on the containing document library instead.
- Ask the business user to confirm that the Account folder is visible in OneDrive, Finder, or File Explorer before requesting the local path.
- Do not continue with local folder creation until the business user provides or selects the synced Account-folder path.
- For a new project, after creating the Opportunity folder, ask the business user to wait for OneDrive to report a healthy sync. Then use `list_folder_items` once to check whether the folder appears in SharePoint. If it is not yet visible, report the sync as pending; do not retry indefinitely.
- For an existing project, confirm that the business user can see the Opportunity folder locally after OneDrive finishes syncing. Do not create missing folders as a workaround.

## Verify access and readiness

- Ask the business user to confirm that OneDrive is signed into the correct work account and reports the Account shortcut as healthy.
- Before creating folders or relying on an existing project, run `scripts/prepare-opportunity-folder.py --check-only` with the selected mode, Account path, and project name. It checks local readiness without changing folders, and it does not create or backfill `AGENTS.md`; the non-check-only `--mode existing` run described under "Join an existing project" does that.
- Treat a successful local check as evidence that Codex can access the local path, not as proof of SharePoint Edit access or successful OneDrive upload.
- For a new project, use the folder's later appearance in SharePoint after healthy OneDrive sync as the practical end-to-end verification.
- For an existing project, do not create a test file or folder to verify access. Report the user-confirmed Edit access and local readiness separately.

## Locate messaging context

- For each client messaging app, follow its reference workflow to locate candidate sources and report only the metadata permitted by that workflow.
- Do not read messages, files, or threads unless the relevant reference explicitly allows a consented fallback. Do not create, rename, or modify messaging channels in this skill.

## Inventory channel sources

- Create a concise messaging-source inventory using channel metadata; for an explicitly consented conversation search, include only the matched conversation location and status.
- For each candidate, record the platform, parent location when applicable, channel name, available purpose or description, active or archived state when available, matched terms, and a status of confirmed, candidate, or excluded.
- Include the connection state for each platform: **usable** (known source returned), **authenticated—scope not verified** (connector responded but known source was absent), **not connected** (connector call could not authenticate), or **not yet supported** (no matching platform reference).
- Mark a channel as confirmed only when the business user identifies it as relevant. Do not infer confirmation from a name match alone.
- When a relevant channel name is vague or its description is missing, advise the business user to ask the channel owner to improve it. Recommend a name that distinguishes the account, project, and workstream or purpose, plus a short description of the channel's scope and intended use.
- Do not rename channels, edit descriptions, create channels, or ask for message content in this skill.

## Maintain the project communications record

- Treat `<Opportunity folder>/Agent Inbox/source-context.yaml` as the implementation file for a project-owned, living project communications record of the relevant client messaging sources. Do not place this file in the reusable skill folder or treat it as a cross-project registry.
- In user-facing language, call this the **project communications record**. Do not call it a config file, YAML file, metadata, or a source-context record; do not show its file path, IDs, or schema unless the user specifically asks for technical detail.
- After the business user confirms the selected Opportunity folder and relevant sources, ask for confirmation in plain language: "Would you like me to save these confirmed messaging locations in the project communications record so they are easy to find next time?" Do not create or update it when the user declines or when the Opportunity folder is not locally writable.
- On the first confirmed write, create a concise YAML record with the account and opportunity names, a `last_verified` date, each platform's connection state, and confirmed locations only. Use the platform's reference workflow to identify the safe metadata to record. Do not record message text, files, threads, credentials, or OAuth data.
- On each later use of this skill for the same Opportunity folder, read the existing record before locating channels. Reconcile it against the current metadata probes: add newly confirmed relevant channels, refresh changed metadata and `last_verified`, and mark unavailable previously confirmed channels as `scope_not_verified` rather than deleting them.
- Keep candidates and excluded channels in the conversational setup summary, not in the living record. Add a channel only after the business user confirms that it is relevant to the project.
- Do not claim this record updates automatically when a new channel is created. It is refreshed only when this skill or a later authorized source-inventory workflow runs and the user approves the update.
- Use this shape, omitting unavailable optional IDs or descriptions:

  ```yaml
  account: <account name>
  opportunity: <opportunity name>
  last_verified: <YYYY-MM-DD>
  messaging_platforms:
    - name: <platform name>
      connection_state: usable
      locations:
        - name: <channel or location name>
          parent_name: <team, workspace, or other parent when available>
          identifiers:
            channel_id: <available ID>
            parent_id: <available parent ID>
          description: <available purpose or description>
          status: confirmed
  ```

## Handoff to discovery

- Treat source discovery as metadata-only except for an explicitly consented platform-specific conversation search. This skill ends after setup and candidate reporting.
- State the discovered sources, channel inventory, and project communications record status in plain language for the next task, such as: "SharePoint: `Acme/<opportunity-name>`; messaging: `#account-acme` (confirmed); project communications record: updated."
- Require the later discovery or analysis task to obtain explicit user confirmation before retrieving any messages, files, threads, or document contents.

## Output expectations

- Keep status updates simple and encouraging for non-technical users.
- End with a compact, visually scannable **Setup readiness** checklist covering local environment, OneDrive and Opportunity-folder, SharePoint, client messaging apps, and channel inventory. Use this legend and order:

  ```text
  ✅ Completed automatically
  🔎 Verified — user action still needed
  ⚠️ Blocked or limited by connector/runtime
  ```

- Give every checklist item a status marker and a short plain-language result. Use `✅` only for work actually completed or for a known source returned by its connector probe; do not use it for a successful API response alone.
- Follow the checklist with one concise **Next step** when any item is `🔎` or `⚠️`. Omit it only when every required setup item is complete.
- State the next connector action whenever a client messaging app is authenticated but scope is not verified.

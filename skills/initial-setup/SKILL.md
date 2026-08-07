---
name: initial-setup
description: Bootstrap a non-technical business user's local discovery environment for accelerated discovery work. Use when Codex needs to verify or install Python and Node.js/npm; resolve an existing SharePoint Account folder; guide its one-time OneDrive connection; set up a business user who is starting a new project or joining an existing project; and locate existing Slack and Microsoft Teams channels tied to that account or opportunity.
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
5. Confirm SharePoint Edit access and local write readiness for the selected path before creating folders or relying on the path for future files.
6. Locate the matching Slack channel.
7. Locate the matching Teams team/channel.
8. Summarize the connected sources, their candidate locations, and any connector limitations for a later discovery task.

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

## Handle connector connections

- Treat Slack, Teams, and SharePoint connector authentication as Codex runtime setup rather than OS-specific local setup.
- If a connector is not connected, direct the user through the Codex connector sign-in flow instead of giving shell commands.
- Once the connector is connected, use the same connector workflow on both macOS and Windows.

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
    Contract & SOW/
    Governance/
    Stakeholders/
    Working Docs/
    Deliverables/
    Reference/
```

- If an Opportunity folder with that project name already exists, stop and ask the business user whether they meant to join that existing project. Do not add template folders to it.

### Join an existing project

- Ask the business user to identify the existing Opportunity folder by name from the synced Account folder.
- Ask the business user to confirm they have SharePoint **Edit** access to that Opportunity folder before treating it as ready for future file additions.
- Run `scripts/prepare-opportunity-folder.py --mode existing --account-root <synced-account-path> --opportunity-name <project-name>` to verify the local folder and report the six template-folder statuses.
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
- Before creating folders or relying on an existing project, run `scripts/prepare-opportunity-folder.py --check-only` with the selected mode, Account path, and project name. It checks local readiness without changing folders.
- Treat a successful local check as evidence that Codex can access the local path, not as proof of SharePoint Edit access or successful OneDrive upload.
- For a new project, use the folder's later appearance in SharePoint after healthy OneDrive sync as the practical end-to-end verification.
- For an existing project, do not create a test file or folder to verify access. Report the user-confirmed Edit access and local readiness separately.

## Locate Slack context

- Use `slack_search_channels` to find likely existing channels by account, opportunity, project, or engagement name.
- Search public and private channels when the user indicates both may be in play.
- Prefer exact or near-exact name matches before broader topical matches.
- Report the best candidates with channel name, purpose/topic when available, whether the channel is archived, and the account, project, or workstream terms that matched.
- Do not read channel messages, files, threads, or other channel content while locating candidates.
- Do not retrieve Slack content in this skill, even if the user identifies a preferred channel.
- Do not create Slack channels in this skill.

## Locate Teams context

- Use `list_teams` first when the user names a team but the exact team ID is unknown.
- Use `list_channels` after the team is resolved to find the likely channel.
- Report the best candidates with the resolved team and channel names, channel description when available, and the account, project, or workstream terms that matched.
- Do not use message search or read channel messages, files, threads, or other channel content while locating candidates.
- Do not retrieve Teams content in this skill, even if the user identifies a preferred team or channel.
- Do not create Teams teams or channels in this skill.

## Inventory channel sources

- Create a concise Slack and Teams source inventory for the business user using channel metadata only.
- For each candidate, record the platform, resolved team when applicable, channel name, available purpose or description, active or archived state, matched terms, and a status of confirmed, candidate, or excluded.
- Mark a channel as confirmed only when the business user identifies it as relevant. Do not infer confirmation from a name match alone.
- When a relevant channel name is vague or its description is missing, advise the business user to ask the channel owner to improve it. Recommend a name that distinguishes the account, project, and workstream or purpose, plus a short description of the channel's scope and intended use.
- Do not rename channels, edit descriptions, create channels, or ask for message content in this skill.

## Handoff to discovery

- Treat source discovery as metadata-only. This skill ends after setup and candidate reporting.
- State the discovered sources and the channel inventory in plain language for the next task, such as: "SharePoint: `Acme/<opportunity-name>`; Slack: `#account-acme` (confirmed); Teams: `Acme > Opportunity` (candidate)."
- Require the later discovery or analysis task to obtain explicit user confirmation before retrieving any messages, files, threads, or document contents.

## Output expectations

- Keep status updates simple and encouraging for non-technical users.
- Distinguish clearly between:
  - completed automatically
  - verified but still needs user action
  - blocked by connector/runtime limitation
- End with a short readiness summary covering local environment, OneDrive and Opportunity-folder, SharePoint, Slack, Teams, and channel-inventory status.

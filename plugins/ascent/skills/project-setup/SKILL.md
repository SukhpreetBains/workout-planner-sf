---
name: project-setup
description: Guide a macOS Codex user through creating a local Codex project for a confirmed Account or Opportunity folder. Use after the folder exists locally and its exact Account name, Opportunity name, and path are known. Do not use this skill to edit Codex global state or automate the project-creation interface.
---

# Project Setup

Help the user add one confirmed local Opportunity folder to Codex. Prefer the
Opportunity folder so Codex access stays limited to the current engagement. Use
the Account folder only when the user explicitly wants one Codex project to
cover every Opportunity beneath that Account.

## Before showing the steps

- Require the confirmed Account name, Opportunity name, local Account path, and
  local Opportunity path from the calling workflow. Do not guess any name or
  path.
- If the calling workflow has not already confirmed that the user uses Codex,
  ask whether they use Codex for this Opportunity. If they do not, return to the
  calling workflow without showing these instructions.
- These screenshots show the Codex macOS interface and the macOS file picker.
  On another operating system, explain that the controls may differ and give
  the same folder-selection outcome without claiming the screenshots match.
- Do not use browser control, edit `~/.codex/.codex-global-state.json`, or edit
  `~/.codex/config.toml`. Project creation is a user-controlled Codex action.

## Show the guided setup

Before the numbered instructions, say:

> Create the Codex project with the Account or Opportunity folder as its scope:

Present the following numbered instructions. Substitute the confirmed Account
and Opportunity names everywhere placeholders appear. Resolve every image to
its absolute filesystem path so it renders in the app, and place each image
immediately below the instruction it supports.

1. In the upper-left corner of Codex, hover over **Projects**, then click the
   **+** button.

   Show [the Projects add-button example](assets/projects-add.png) with alt text
   identifying the highlighted **+** button beside **Projects**.

2. Select **Local**, then click **Next**.

   Show [the local-project example](assets/project-type-local.png) with alt text
   identifying the highlighted **Local** option and **Next** button.

3. Click **Add folders Codex can read and edit**.

   Show [the source-folder example](assets/add-source-folder.png) with alt text
   identifying **Add folders Codex can read and edit**.

4. If the confirmed folder is in OneDrive, click **OneDrive** on the left side.
   For a local-only workspace elsewhere on the computer, select its confirmed
   Finder location instead and explain that the screenshot shows the OneDrive
   path.

   Show [the OneDrive example](assets/onedrive-location.png) with alt text
   identifying the highlighted **OneDrive** location.

5. In OneDrive, open **<Account folder name>**, select
   **<Opportunity folder name>**, then click **Open**. If the user explicitly
   chose Account-wide scope, select **<Account folder name>** instead. Tell the
   user to follow the confirmed names supplied in the instructions, not the
   example Account name visible in a screenshot.

6. If Codex did not fill the project name automatically, enter
   **<Opportunity name>**. Confirm that the selected source folder is correct,
   then click **Create project**.

   Show [the Create project example](assets/create-project.png) with alt text
   identifying the selected source folder and highlighted **Create project**
   button. State that the Account name in the screenshot is only an example.

## Explain projects and conversations

After the steps, explain in plain language:

- A Codex project groups conversations around one or more source folders. Codex
  can read and edit the folders the user selected, subject to the active
  permission mode, and project instructions such as `AGENTS.md` can guide work
  within that folder.
- Continue an existing conversation when the next request directly builds on
  the same goal, decisions, and unfinished work.
- Start a new conversation for a separate feature, deliverable, investigation,
  or workstream. This keeps unrelated history out of the new task while the
  project still provides access to the same source folder.
- To start a new conversation inside a project, hover over the project name and
  click the new-conversation icon.

Show [the project conversation example](assets/new-project-conversation.png)
with alt text identifying the highlighted new-conversation icon beside a Codex
project.

## Continue the calling setup

Ask, **"Have you created the Codex project?"** Use the host's structured-question
tool when available, with short choices for **Yes, it is created** and **Not yet**.
Record the answer for the setup-readiness report, but continue the calling
workflow regardless of the answer. Treat a dismissed prompt or any other answer
as **not verified** and continue. Do not repeat the instructions unless the user
asks for help.

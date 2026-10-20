# Ascent Workflow Overview

Ascent gives a project team a governed path from source material to evidence-backed project knowledge and client deliverables. Agent hosts discover the workflows from the installed skills in `skills/`; this overview explains how the currently executable workflows fit together without duplicating their detailed instructions. Before recommending a workflow, inspect the installed skills so availability stays current as the plugin evolves.

## Start with identity-only setup

Run `ascent-initial-setup` when starting a new Project or joining an existing one. It prepares or resumes the workspace, confirms storage and communications, initializes trackers and search, and records only the confirmed Account and Project identity. It preserves existing project metadata and readable overview content.

Initial setup does not ask for optional engagement details and does not inspect or process source documents. After its final checklist, open a fresh agent chat with the same project folder open. Drag documents into that chat, or find the files on your computer and place them in the linked `workspace/inbox/` review inbox. Then run `workspace-add` to turn the sources into structured project content and proposed tracker updates for review. Use this prompt:

```text
Use workspace-add to ingest the documents I attached or placed in this project workspace inbox.
```

`workspace-add` prepares evidence-backed proposals. If it finds proposals, the review inbox is for approving them afterward; only `workspace-review` writes approved changes into trackers.

## Knowledge lifecycle

0. **Collect new material (optional):** `workspace-collect` checks the saved Slack channels and threads and recurring Teams meetings marked for collection, weekly or daily, and places new material in `workspace/inbox/`. It tells the user what arrived and never ingests on its own.
1. **Ingest documents:** `workspace-add` files new material, records its provenance, extracts evidence-backed findings, proposes tracker updates, and refreshes search. It does not change trackers.
2. **Review proposed updates:** `workspace-review` lets a person approve, edit, or reject each proposal with its source evidence. It is the only workflow that writes approved changes into trackers.
3. **Investigate or summarize governed evidence:** `investigate-project` maps confirmed knowledge locations or retrieves bounded, cited evidence for a specific task. `workspace-summarize` turns approved tracker knowledge and filed sources into evidence-grounded narratives without changing trackers.
4. **Create deliverables:** `create-deliverables` uses the governed project evidence to create draft client deliverables in `workspace/draft-deliverables/` for review and human promotion.

```text
workspace-add
    -> workspace-review
    -> investigate-project or workspace-summarize
    -> create-deliverables
```

The workflow is intentionally separated. Source processing proposes knowledge, human review governs tracker changes, investigation and summaries remain evidence-grounded, and deliverables stay in the draft workspace until a person promotes them.

## Workspace boundaries

- Agent-created project work belongs in `workspace/`.
- Draft output artifacts belong in `workspace/draft-deliverables/`.
- `Deliverables/` is reserved for human-promoted material.
- Existing files, metadata, and tracker rows are preserved by resumable setup.
- Planned skills marked as non-executable in the repository are not part of this workflow.

For step-by-step setup and operating guidance, see the repository [Project Workspace Walkthrough](../../docs/project-workspace-walkthrough.md).

# Agent Workspace — {{OPPORTUNITY_NAME}}

Use `workspace/` for all agent-created project work, including working documents, meeting notes, project summaries, trackers, proposed updates, indexes, and project source records.

```text
{{OPPORTUNITY_NAME}}/
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

Preserve existing files when initializing or resuming the workspace. Use the relevant skill for governed operations: `workspace-ingest-documents`, `workspace-review-updates`, or `workspace-summarize`.

Do not create agent working files in `Deliverables/`. Store agent-created output artifacts, including decks, documents, and generated sites, in `workspace/draft-deliverables/`. A human may promote reviewed material from `workspace/` into the appropriate delivery phase.

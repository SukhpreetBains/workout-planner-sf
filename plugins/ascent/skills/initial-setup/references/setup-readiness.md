# Setup Readiness Contract

This file is the authoritative definition of the initial-setup readiness report. Other instructions should link here instead of copying its headings or item list.

## Status groups

Place every checklist item under exactly one group, preserving this order:

1. **✅ Completed automatically**: Setup completed and verified the item without remaining user action.
2. **🔎 Verified, user action still needed**: Setup verified the current state, but a named user action remains.
3. **⚠️ Blocked or limited by connector/runtime**: A connector, host boundary, missing dependency, or runtime condition prevented verification or completion.

## Checklist

Cover these items in this order:

1. Environment, including Python, the cached workspace runtime, and its `.system/.venv-path` pointer.
2. Background plugin updates: installed and running daily, declined by the user this session, or installed but blocked pending a macOS Full Disk Access grant (report the exact remediation step given by `--install`).
3. Storage, including storage mode, applicable shared storage, and the confirmed local Opportunity path.
4. Workspace structure.
5. Host folder access, when applicable — verified only when the confirmed Opportunity folder is open for future conversations.
6. Communications, including messaging sources and the project communications record.
7. Trackers.
8. Identity metadata for the confirmed Account and Opportunity.
9. Industry flavor, if any packs were available to offer — which one was selected, or that none was applicable. Omit this item entirely when no packs exist to offer.
10. Search index.
11. Workflow guidance, linked to the plugin workflow overview.

## Incomplete items

Give one concise next step whenever anything is incomplete. Phrase required user choices as actionable prompts. For example, ask whether Slack or Microsoft Teams should be verified now, or request the known channel, team, or location needed to continue.

## First-document action

After the checklist groups, end the report with a concrete **Next: Add your first source document** action. Do not ask whether documents are present or inspect the inbox during setup.

1. Name the confirmed absolute `<Opportunity folder>/workspace/inbox/` path. Tell users with a document to place it there now; if a document is already there, leave it in place. Users without one can follow this action when their first source arrives.
2. Tell the user to finish setup first, then start a fresh conversation with the same Opportunity folder open before ingestion. Explain that a new conversation gives document processing room without carrying setup history into its context.
3. Provide this copyable starter prompt:

```text
Use workspace-add to process the documents in this Opportunity workspace inbox.
```

State that `workspace-add` files the source and prepares evidence-backed proposals. If it finds proposals, the review inbox is for approving them afterward; trackers change only after approval through `workspace-review`.

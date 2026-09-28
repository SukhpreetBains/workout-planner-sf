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
5. Host project status, when applicable.
6. Communications, including messaging sources and the project communications record.
7. Trackers.
8. Identity metadata for the confirmed Account and Opportunity.
9. Industry flavor, if any packs were available to offer — which one was selected, or that none was applicable. Omit this item entirely when no packs exist to offer.
10. Search index.
11. Workflow guidance, linked to the plugin workflow overview.
12. Fresh-chat document next step, framed conditionally for users with documents and including the copyable starter prompt without asking whether documents are present.

## Incomplete items

Give one concise next step whenever anything is incomplete. Phrase required user choices as actionable prompts. For example, ask whether Slack or Microsoft Teams should be verified now, or request the known channel, team, or location needed to continue.

For the document next step, name the confirmed absolute `<Opportunity folder>/workspace/inbox/` path. State that files placed there are what `workspace-add` will process, and include:

```text
Use workspace-add to process the documents in this Opportunity workspace inbox.
```

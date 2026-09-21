# Messaging Confirmation

Use this reference only after the Account, Opportunity, and local path are confirmed.

## Confirm messaging sources

- Ask whether Slack or Microsoft Teams contains relevant project conversations. Treat a platform as a default only after the user confirms it.
- Request one known channel, team and channel, or distinctive Account or workstream term for each confirmed platform. Then read [Slack](slack.md) or [Microsoft Teams](microsoft-teams.md) for that branch.
- Treat a successful connector response as authentication, not proof of usable project access. Mark a platform usable only after the expected source is returned.
- Report no-match results as **scope not verified**. Do not infer that a channel does not exist.
- Do not read messages, files, or threads unless the platform reference explicitly permits a consented fallback.
- Do not create, rename, or modify messaging channels during setup.
- If a source decision remains unconfirmed, ask the next actionable setup question instead of ending with a passive incomplete status.

## Maintain the project communications record

Use `<Opportunity folder>/workspace/.system/source-context.yaml` for confirmed SharePoint, messaging, and other external project locations. Read [the source-context contract](source-context.md) before the first write.

- Ask before the first write: **"Would you like me to save these confirmed project locations so they are easy to find next time?"**
- Keep `account`, `opportunity`, and `last_verified` at the top level.
- Store source locations and access state only. Never store message text, document contents, credentials, OAuth data, or permission payloads.
- Save only user-confirmed locations. Keep candidates and exclusions in the conversational setup report.
- Reconcile an existing record and preserve unknown fields. Mark unavailable prior sources as `scope_not_verified` instead of deleting them.
- Keep `workspace/.system/sources.yaml` as the separate ledger of ingested documents.

Use `scripts/manage-source-context.py` to manage the record.

# Codex Connector Routing

This is a capability snapshot, not a promise of fixed connector IDs or tenant scopes. At runtime, inspect the surfaced tools and use the closest current read operation. Authentication is limited to the connected user's accessible content; exact OAuth scopes and tenant policies are not exposed by the skill and must not be guessed.

Snapshot observed 2026-08-04:

## Slack

- Resolve channels: `slack_search_channels`
- Search public messages/files: `slack_search_public`
- Search public and private messages/files: `slack_search_public_and_private`
- Read bounded channel history: `slack_read_channel`
- Expand a relevant thread: `slack_read_thread`
- Read a referenced canvas: `slack_read_canvas`

Use channel and date modifiers, return concise response formats when available, and start with at most 20 search hits. Private search requires explicit user consent unless the project manifest records `allow_private_search: true`. Respect rate-limit responses and connector retry guidance.

## Microsoft Teams

- Enumerate Teams when a name must be resolved: `microsoft_teams_list_teams`
- Enumerate channels within a known team: `microsoft_teams_list_channels`
- Enumerate chats when a chat is the recorded source: `microsoft_teams_list_chats`
- Search for narrow terms: `microsoft_teams_search`
- Fetch a selected result or resource: `microsoft_teams_fetch`

Mention metadata is more reliable on fetched history than on search hits. Channel-message unread state is not available. For unbounded channel history, start with at most 50 messages when a bounded history operation is surfaced.

## Microsoft SharePoint

- Validate a known site: `microsoft_sharepoint_get_site`
- Browse an exact folder: `microsoft_sharepoint_list_folder_items`
- Search within a known site/folder scope: `microsoft_sharepoint_search`
- Fetch a selected document or item: `microsoft_sharepoint_fetch`

Prefer canonical URLs and exact metadata paths returned by browse/search. Keyword search may omit unsupported or oversized file types, so browse an exact recorded folder when search is incomplete. Fetch Office files as text for retrieval; raw package download is only needed for document editing.

## Runtime drift

Tool prefixes and optional operations can change by plugin version or session. Route by semantic capability, not a copied fully-qualified MCP name. If a required operation is not surfaced, record the access gap and continue with other manifest sources; do not widen to unrelated systems.

# Connector Routing by Capability

Treat connectors as interchangeable systems with different surfaced operations. Inspect the current runtime and select the narrowest read capability below; do not assume tool names, API versions, tenant scopes, or authentication behavior.

## Chat systems

Resolve a named channel, team, or chat; search within it using project terms and date filters; read a bounded message slice; and expand a selected thread only when it contains a likely decision or requirement. Start with no more than 20 search hits or 50 history messages for retrieval. A map-mode pass uses the stricter cap in `discover.md`.

Search private content only with explicit user consent or `source_policy.allow_private_search: true`. Preserve message permalinks or stable IDs for selected evidence.

## Document and knowledge systems

Validate a recorded site, workspace, library, or folder; browse the exact location; search only within that scope; then fetch selected documents as text. Prefer canonical URLs and returned stable paths. If keyword search has known file-type gaps, inspect the recorded folder metadata before widening scope.

For SharePoint, route from the identifiers imported from the project communications record:

1. Validate `hostname` plus `site_path` with the runtime's site-resolution capability.
2. Resolve the recorded `drive_id` or `drive_name`; list site drives only when the shared record lacks that identifier.
3. List immediate items at the recorded `folder_path` to confirm the folder boundary.
4. Search with the same hostname, site path, and folder path, or fetch an exact URL returned from that scope.

Do not use recent-document lists to rediscover a site, and do not treat connector authentication as proof that the recorded folder is accessible.

## Local sources

Use the recorded workspace-relative path and its include/exclude filters. Search exact filenames or narrow text matches first, then read only selected files or sections.

## Unavailable capabilities

If the runtime cannot resolve, search, or read a needed recorded source, report the access gap and continue with other manifest sources. Do not substitute an unrelated system or broaden beyond manifest scope. Respect connector rate limits and retry guidance.

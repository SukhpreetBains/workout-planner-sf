# Project Communications Record Contract

Use `<Opportunity folder>/workspace/.system/source-context.yaml` as the project-owned source-location record shared by setup, discovery, and retrieval. Store references and access state only—never message text, document contents, credentials, OAuth data, or permission payloads.

`initial-setup` owns the contract. Later skills may add or refresh confirmed locations but must preserve unknown fields and previously confirmed locations.

## Shape

```yaml
schema_version: 1
account: "Acme"
opportunity: "Service Transformation"
last_verified: "2026-08-12"
sharepoint_locations:
  - id: "engagement-folder"
    name: "Service Transformation"
    locator: "https://contoso.sharepoint.com/sites/Consulting/Shared%20Documents/Acme/Service%20Transformation"
    identifiers:
      hostname: "contoso.sharepoint.com"
      site_path: "/sites/Consulting"
      drive_id: "b!..."
      drive_name: "Shared Documents"
      folder_path: "Acme/Service Transformation"
    purpose: "Canonical engagement workspace"
    status: "confirmed"
    access:
      state: "available"
      reason: "Folder identity was confirmed during setup."
messaging_platforms:
  - name: "Slack"
    connection_state: "usable"
    locations:
      - id: "slack-account-acme"
        name: "account-acme"
        parent_name: "Client workspace"
        locator: "slack://T123/C456"
        identifiers:
          parent_id: "T123"
          channel_id: "C456"
        description: "Account delivery coordination"
        purpose: "Project decisions and status"
        status: "confirmed"
        access:
          state: "available"
          reason: "The confirmed channel was returned by the connector."
project_sources: []
```

## Rules

- Keep `account`, `opportunity`, and `last_verified` at the top level.
- Record SharePoint folders in `sharepoint_locations`, messaging locations beneath their platform in `messaging_platforms`, and local/web/other references in `project_sources`.
- Use a stable lowercase `id` for every location. Preserve it when names or URLs change.
- Use `status: confirmed` only after user confirmation. Use `scope_not_verified` when the connector responds but cannot resolve the expected location.
- Use `access.state` values `available`, `unavailable`, or `unknown`; keep the reason short and non-sensitive.
- For SharePoint, retain the canonical URL plus every identifier exposed by the runtime: `hostname`, `site_path`, `drive_id`, `drive_name`, and `folder_path`. Omit unavailable identifiers rather than inventing them.
- Optional retrieval fields are `authority`, `priority`, `query_hints`, `include`, `exclude`, `time_window`, `freshness_hours`, `sensitivity`, and `enabled`.
- Keep candidates and excluded locations in the conversational report. Persist only confirmed locations or previously confirmed locations whose current scope is no longer verified.

Use `scripts/manage-source-context.py` to initialize, validate, update, or export this record. The script accepts the original minimal messaging-only shape and preserves compatible fields while adding the extended SharePoint and retrieval metadata.

# Project Context Contract v1

Use `.codex/project-context/manifest.json` as the stable handoff between discovery, retrieval, and downstream skills.

## Required shape

```json
{
  "schema_version": 1,
  "project": {
    "id": "project-slug",
    "name": "Project name",
    "objective": "The outcome currently being pursued",
    "current_phase": "design",
    "workspace_roots": ["."],
    "technology": ["Salesforce"],
    "terms": ["REWS means Real Estate and Workplace Services"],
    "stakeholders": ["Product owner: Example Person"],
    "constraints": ["Do not copy customer data into the repository"],
    "updated_at": "2026-08-04T12:00:00Z"
  },
  "source_policy": {
    "default_freshness_hours": 168,
    "max_excerpt_chars": 1200,
    "max_total_chars": 12000,
    "allow_private_search": false
  },
  "sources": [
    {
      "id": "requirements",
      "kind": "local",
      "label": "Requirements",
      "locator": "specs/project/design.md",
      "purpose": "Canonical scope and acceptance criteria",
      "authority": "canonical",
      "priority": 5,
      "query_hints": ["acceptance criteria", "architecture"],
      "include": [],
      "exclude": ["generated reports"],
      "time_window": {"start": null, "end": null},
      "freshness_hours": 168,
      "sensitivity": "internal",
      "enabled": true,
      "last_confirmed_at": "2026-08-04T12:00:00Z"
    }
  ],
  "open_questions": [],
  "created_at": "2026-08-04T12:00:00Z",
  "updated_at": "2026-08-04T12:00:00Z"
}
```

## Field rules

### Project

- `id`: Stable lowercase slug. Do not repurpose an ID for a different project.
- `name`: User-facing project name.
- `objective`: Current outcome, not a generic business description.
- `current_phase`: Short free text such as `discovery`, `design`, `build`, or `validation`.
- `workspace_roots`: Workspace-relative paths when possible. Use absolute paths only for roots outside the workspace.
- `technology`, `terms`, `stakeholders`, `constraints`: Compact strings. Keep detailed prose elsewhere.

### Source policy

- `default_freshness_hours`: Default age after which remote cached context should be reconsidered.
- `max_excerpt_chars`: Maximum persisted characters for one excerpt.
- `max_total_chars`: Maximum persisted excerpt characters in one ranked context pack.
- `allow_private_search`: Whether private-message search was explicitly permitted. `false` never prevents direct reads of a source the user explicitly supplied and authorized; it prevents unbounded private search.

### Sources

- `id`: Unique lowercase identifier using letters, digits, and hyphens.
- `kind`: One of `local`, `slack`, `teams`, `sharepoint`, `web`, or `other`.
- `locator`: Workspace-relative local path, canonical URL, or stable connector identifier.
- `purpose`: Why a future task should use this source.
- `authority`: `canonical`, `supporting`, or `historical`.
- `priority`: Integer from 1 (lowest) to 5 (highest).
- `query_hints`: Terms that narrow connector search. Do not paste document contents.
- `include` and `exclude`: Optional path, channel, file-type, author, or topic filters.
- `time_window`: Optional ISO dates or timestamps. `null` means unbounded.
- `freshness_hours`: Per-source override. Use `0` only for immutable content.
- `sensitivity`: `public`, `internal`, `confidential`, or `restricted`.
- `enabled`: Keep a known source but skip retrieval when `false`.
- `last_confirmed_at`: When the source identity and intended scope were last confirmed.

## Invariants

- Store locations and retrieval hints, not credentials or bulk source content.
- Keep source IDs stable so cached summaries remain addressable.
- Preserve unknown values explicitly rather than inventing them.
- Update `updated_at` whenever material fields change.
- Validate after every write.

## Consumer behavior

A downstream skill must read `brief.md` first, load the manifest only as needed, and search outside listed sources only when the manifest is incomplete for the current task. It must explain any scope expansion and offer to update the manifest afterward.

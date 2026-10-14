# Context Contract v1

The shared contract for the manifest both modes read and write, plus
the chunk, pack, and access-gap formats evidence mode produces from it.

Use `workspace/.system/source-context.yaml`, created by `ascent-initial-setup`, as the project-owned source-location record. Use `workspace/.system/project-context/manifest.json` as its machine-local retrieval projection and stable handoff to ranking scripts. Import the shared record before retrieval; do not maintain conflicting source identities in the local projection.

## Manifest

### Required shape

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
  "source_context": {
    "path": "workspace/.system/source-context.yaml",
    "last_imported_at": "2026-08-04T12:00:00Z",
    "source_count": 3
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
      "access": {
        "state": "available",
        "reason": "Access confirmed during discovery."
      },
      "last_confirmed_at": "2026-08-04T12:00:00Z"
    }
  ],
  "discovery_runs": [
    {
      "recorded_at": "2026-08-04T12:00:00Z",
      "sources_considered": 6,
      "sources_recorded": 3,
      "connector_calls": 4,
      "items_inspected": 18,
      "characters_inspected": 3200,
      "estimated_tokens": 800,
      "exploration_caps": {
        "local": 30,
        "chat": 30,
        "document": 30,
        "other": 10
      }
    }
  ],
  "open_questions": [],
  "created_at": "2026-08-04T12:00:00Z",
  "updated_at": "2026-08-04T12:00:00Z"
}
```

### Field rules

#### Project

- `id`: Stable lowercase slug. Do not repurpose an ID for a different project.
- `name`: User-facing project name.
- `objective`: Current outcome, not a generic business description.
- `current_phase`: Short free text such as `discovery`, `design`, `build`, or `validation`.
- `workspace_roots`: Workspace-relative paths when possible. Use absolute paths only for roots outside the workspace.
- `technology`, `terms`, `stakeholders`, `constraints`: Compact strings. Keep detailed prose elsewhere.

#### Source policy

- `default_freshness_hours`: Default age after which remote cached context should be reconsidered.
- `max_excerpt_chars`: Maximum persisted characters for one excerpt.
- `max_total_chars`: Maximum persisted excerpt characters in one ranked context pack.
- `allow_private_search`: Whether private-message search was explicitly permitted. `false` never prevents direct reads of a source the user explicitly supplied and authorized; it prevents unbounded private search.

#### Source-context projection

- `path`: Workspace-relative path to the setup-generated project communications record when possible.
- `last_imported_at`: When shared source references were last synchronized into this local manifest.
- `source_count`: Number of shared source references present at import time.

Run `project_context.py import-source-context` after setup or map-mode work changes the shared record. Import updates matching source IDs and preserves local-only entries; it never deletes an unrelated cached source merely because a narrow shared update omitted it.

#### Sources

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
- `access`: A bounded access record with `state` `available`, `unavailable`, or `unknown`, and a short non-sensitive `reason`. New source records must include it. Older manifests may omit it and are treated as legacy sources until refreshed.
- `last_confirmed_at`: When the source identity and intended scope were last confirmed.

Map mode uses `access.state` to distinguish a resolved source from a permission or capability gap. An `unavailable` or `unknown` source remains a valid reference; it is not an invitation to search a different location.

**Fields evidence mode relies on**: `project.objective`, `project.terms`, and `project.current_phase` expand the task query; `source_policy` sets privacy and excerpt budgets; `sources[].purpose`, `authority`, `priority`, `query_hints`, `include`, `exclude`, `time_window`, `freshness_hours`, `sensitivity`, `enabled`, and `access` control selection and scoring; source `id` values are stable join keys for chunks and cached hierarchy paths. Only sources with `access.state: available` may be retrieved — an `unavailable` or `unknown` source remains in the manifest and becomes an access gap for the current retrieval; evidence mode must preserve its label, locator, state, and short reason, and must not try another connector, request broader permissions, or widen the source search unless the user explicitly asks.

#### Discovery runs

`discovery_runs` is an append-only, bounded measurement log for lightweight source discovery. It stores counts only, never source content. Each entry records:

- `recorded_at`: When the pass finished.
- `sources_considered` and `sources_recorded`: Candidate locations assessed and references added or updated.
- `connector_calls`, `items_inspected`, and `characters_inspected`: The bounded discovery work performed.
- `estimated_tokens`: A runtime-reported input-token total when available, otherwise `ceil(characters_inspected / 4)`.
- `exploration_caps`: Positive per-system item caps stated for the pass. The stable keys are `local`, `chat`, `document`, and `other`.

Keep the most recent 20 entries. Older manifests without this optional field remain valid, but record a run whenever performing a new map-mode pass.

## Invariants

- Store locations and retrieval hints, not credentials or bulk source content.
- Treat the setup-generated project communications record as the shared source of truth and the manifest as a generated local projection.
- Store only the source access state and a short reason; never store permission error payloads, previews, or source content.
- Store discovery measurements as counts only; never add previews or source snippets to `discovery_runs`.
- Keep source IDs stable so cached summaries remain addressable.
- Preserve unknown values explicitly rather than inventing them.
- Update `updated_at` whenever material fields change.
- Validate after every write.

## Consumer behavior

A downstream skill must read `brief.md` first, load the manifest only as needed, and search outside listed sources only when the manifest is incomplete for the current task. It must explain any scope expansion and offer to update the manifest afterward.

## Evidence mode outputs

### Normalized chunk JSONL

Write one JSON object per line:

```json
{
  "chunk_id": "decisions-2026-08-04-001",
  "source_id": "architecture-decisions",
  "title": "Decision to use event-driven updates",
  "text": "Bounded source excerpt or faithful window summary",
  "url": "https://stable-source-link",
  "timestamp": "2026-08-04T12:00:00Z",
  "author": "Source author or Unknown",
  "retrieved_at": "2026-08-04T13:00:00Z",
  "semantic_score": 0.92,
  "is_summary": false
}
```

Required fields are `chunk_id`, `source_id`, and non-empty `text`. Use a unique `chunk_id` within a retrieval run. Omit unknown optional fields instead of inventing them. `semantic_score`, when present, must be between 0 and 1 and represent relevance to the explicit retrieval task.

For a summary derived from a dense window, set `is_summary: true` and include:

```json
{"derived_from":["message-id-1","message-id-2"],"window_start":"...","window_end":"..."}
```

Retain stable source URLs or message IDs so selected facts can be expanded and verified.

### Pack JSON

After ranking, synthesize a pack:

```json
{
  "task": "What the evidence pack supports",
  "overview": "Compact answer grounded in the selected excerpts.",
  "decisions": ["Decision — owner, date, and status when known"],
  "open_questions": ["Material unresolved point"],
  "sources": [
    {
      "source_id": "architecture-decisions",
      "summary": "Why this source matters and what it establishes.",
      "excerpts": [
        {
          "chunk_id": "decisions-2026-08-04-001",
          "source_id": "architecture-decisions",
          "title": "Decision to use event-driven updates",
          "text": "Selected evidence",
          "url": "https://stable-source-link",
          "timestamp": "2026-08-04T12:00:00Z",
          "author": "Example Person",
          "retrieved_at": "2026-08-04T13:00:00Z",
          "_ranking": {"score": 91.4}
        }
      ]
    }
  ]
}
```

`persist_context.py` verifies source IDs, enforces excerpt limits, writes the hierarchy, and records manifest hash and refresh state. It intentionally retains cached source folders not touched by the current run; a narrow task must not erase unrelated context.

### Access gaps

Retrieval runs may include an `access_gaps` array in the pack, or pass the gap JSON emitted by `rank_context.py` to `persist_context.py`. Each gap contains `source_id`, `label`, `locator`, `state`, `reason`, and `recorded_at`. Gaps are written to `state.json` and a separate `Access Gaps` section in `index.md`; they are not mixed with retrieved findings or excerpts.

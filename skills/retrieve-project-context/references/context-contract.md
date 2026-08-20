# Context Retrieval Contract v1

`initial-setup` owns the shared `workspace/.system/source-context.yaml` source-location contract. Discovery maintains confirmed locations and generates `workspace/.system/project-context/manifest.json`; retrieval consumes that local projection without changing shared source identity or scope.

## Manifest fields used by retrieval

- `project.objective`, `project.terms`, and `project.current_phase` expand the task query.
- `source_policy` sets privacy and excerpt budgets.
- `sources[].purpose`, `authority`, `priority`, `query_hints`, `include`, `exclude`, `time_window`, `freshness_hours`, `sensitivity`, `enabled`, and `access` control selection and scoring.
- Source `id` values are stable join keys for chunks and cached hierarchy paths.

Only sources with `access.state: available` may be retrieved. A source with `access.state: unavailable` or `unknown` remains in the manifest and becomes an access gap for the current retrieval. Retrieval must preserve its label, locator, state, and short reason; it must not try another connector, request broader permissions, or widen the source search unless the user explicitly asks.

See the discovery skill's `references/context-contract.md` for the full manifest shape. Version 1 accepts source kinds `local`, `slack`, `teams`, `sharepoint`, `web`, and `other`; authority values `canonical`, `supporting`, and `historical`; and priorities from 1 to 5.

## Normalized chunk JSONL

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

## Pack JSON

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

## Access gaps

Retrieval runs may include an `access_gaps` array in the pack, or pass the gap JSON emitted by `rank_context.py` to `persist_context.py`. Each gap contains `source_id`, `label`, `locator`, `state`, `reason`, and `recorded_at`. Gaps are written to `state.json` and a separate `Access Gaps` section in `index.md`; they are not mixed with retrieved findings or excerpts.

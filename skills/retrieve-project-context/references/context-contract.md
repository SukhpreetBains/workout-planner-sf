# Context Retrieval Contract v1

The discovery skill owns `.codex/project-context/manifest.json`; retrieval consumes it without changing source identity or scope.

## Manifest fields used by retrieval

- `project.objective`, `project.terms`, and `project.current_phase` expand the task query.
- `source_policy` sets privacy and excerpt budgets.
- `sources[].purpose`, `authority`, `priority`, `query_hints`, `include`, `exclude`, `time_window`, `freshness_hours`, `sensitivity`, and `enabled` control selection and scoring.
- Source `id` values are stable join keys for chunks and cached hierarchy paths.

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

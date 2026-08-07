---
name: retrieve-project-context
description: Retrieve, re-rank, trim, and persist task-relevant project context from an existing .codex/project-context/manifest.json. Use when Codex needs evidence from known local files, Slack channels or threads, Microsoft Teams chats or channels, SharePoint sites or folders, or other recorded sources; when long project histories would otherwise consume excessive context; when a cached project briefing should be refreshed; or when downstream work needs a compact summary-to-evidence hierarchy instead of repeated full-source searches. Consume the discovery manifest, prefer fresh cached context, fetch narrowly through available Codex connectors, rank chunks against the current task, and store bounded summaries with provenance.
---

# Retrieve Project Context

Build a task-specific evidence pack from sources already identified by `$discover-project-context`. Keep retrieval narrow, ranking explicit, and persisted context bounded.

## Preconditions

Require `.codex/project-context/manifest.json` beneath the project root. Read `.codex/project-context/brief.md` first, then validate the manifest with the discovery skill's validator when available.

If the manifest is absent or lacks the sources needed for the task, invoke `$discover-project-context` or ask only for the missing location. Do not compensate with an unbounded workspace or connector search.

Read these references before retrieval:

- [references/context-contract.md](references/context-contract.md) for the shared manifest, chunk, and pack contracts
- [references/connector-routing.md](references/connector-routing.md) for current Slack, Teams, and SharePoint routing
- [references/ranking.md](references/ranking.md) for scoring, diversity, and deep-trim rules

## Workflow

### 1. Frame the retrieval task

Write one sentence that captures the decision, deliverable, or question the context must support. Extract key entities, synonyms, ticket IDs, feature names, people, and date constraints. Use the project objective and terminology from the manifest to expand the query without changing its intent.

### 2. Reuse fresh context

Check `.codex/project-context/state.json` and `index.md`.

- Reuse a cached source when its purpose matches the task, it is within `freshness_hours`, and the current request does not demand newer facts.
- Refresh mutable decision, status, issue, and conversation sources when freshness is uncertain.
- Treat `freshness_hours: 0` as immutable and reuse indefinitely unless the locator changes.
- Never imply that cached content is current when the task requires a live status check.

If the cached index fully answers the task, return it with its retrieval timestamp and skip connector calls.

For deterministic cache eligibility checks, use `scripts/cache_context.py` with the recorded manifest, context directory, source ID, and task. Treat a positive result as a reuse decision; do not fetch the source again unless the task requires newer facts.

Before planning retrieval, inspect every task-relevant manifest source's `access` record. Select only `available` sources. For each `unavailable` or `unknown` source, preserve the reference and log an access gap containing its source ID, label, locator, state, and short reason. Do not try an alternative connector, change permissions, search outside the recorded scope, or use a broader source search unless the user explicitly requests that expansion. Continue with accessible evidence and keep access gaps visibly separate from findings.

### 3. Plan bounded retrieval

Select only enabled and accessible sources whose `purpose`, `query_hints`, and filters overlap the task. Start with canonical sources, then add supporting sources only for gaps or corroboration. If a selected source becomes inaccessible at runtime, stop reading it, preserve the reference, and add the retrieval gap without retrying through a broader path.

For every selected source, define:

- the narrow query or exact locator
- the time window
- the initial result limit
- whether thread, attachment, or file expansion is justified
- the freshness reason

Default to 20 search results or 50 history messages per remote source. Paginate only when the current page contains strong unfinished leads. Explain any expansion beyond manifest scope and offer to record the new source later.

### 4. Retrieve through native capabilities

- For local sources, read exact files or narrowly match within recorded directories. Use `rg` for filenames or text; respect `include` and `exclude`.
- For Slack, resolve named channels, search with channel/date/topic modifiers, and expand only relevant channels or threads. Obtain explicit consent before private Slack search unless `source_policy.allow_private_search` is already true.
- For Teams, resolve the team/channel/chat, search narrowly, then fetch only relevant result objects or bounded history.
- For SharePoint, validate the site or folder, browse exact locations when known, search within scope for keywords, and fetch only relevant files.
- For all connectors, use the current runtime's surfaced read tools. Do not hardcode a connector ID from this skill.

Do not persist full connector payloads. Normalize candidates in a temporary JSONL file with one chunk per line:

```json
{"chunk_id":"requirements-001","source_id":"requirements","title":"Acceptance criteria","text":"...","url":"...","timestamp":"2026-08-04T12:00:00Z","author":"...","semantic_score":0.9}
```

Keep chunks coherent: one decision, requirement, thread segment, document section, or roughly 300–800 words. Include stable provenance. Set `semantic_score` from 0 to 1 only when the model has actually assessed task relevance; otherwise omit it and use the deterministic lexical fallback.

### 5. Re-rank and diversify

Run:

```bash
python3 <skill-dir>/scripts/rank_context.py \
  --manifest <workspace-root>/.codex/project-context/manifest.json \
  --chunks <temporary-dir>/chunks.jsonl \
  --task "<retrieval task>" \
  --output <temporary-dir>/ranked.jsonl \
  --top-n 24 \
  --max-per-source 6 \
  --gaps-output <temporary-dir>/access-gaps.json
```

The script combines task relevance, source fit, authority, source priority, recency, and low-signal penalties, then removes near-duplicates and enforces the manifest's total character budget. Review the ranked output: remove unsupported, mis-scoped, or access-inappropriate chunks. Do not promote a chunk merely because it is recent.

`rank_context.py` excludes chunks from unavailable or unknown sources and writes their preserved references to `access-gaps.json`. Keep those gaps separate when building the pack; do not turn an access failure into a missing-source search.

### 6. Deep-trim dense histories when needed

Use the two-pass procedure in [references/ranking.md](references/ranking.md) when a source yields more than 100 messages, 40 chunks, or twice the total character budget. Summarize bounded chronological windows into attributed facts first; rank those window summaries; expand original messages only for the selected facts.

Preserve unresolved disagreement, decision changes, dates, owners, and links. Drop greetings, acknowledgements, repeated bot output, and quoted duplication.

### 7. Synthesize and persist the hierarchy

Create a pack JSON using the contract in [references/context-contract.md](references/context-contract.md). Every claim in the overview or a source summary must be supported by a persisted excerpt or clearly marked as an inference.

Include the `access_gaps` emitted by ranking, even when accessible sources produced useful evidence. The gap list is part of the retrieval result and must not be omitted because it contains no source content.

Run:

```bash
python3 <skill-dir>/scripts/persist_context.py \
  --manifest <workspace-root>/.codex/project-context/manifest.json \
  --pack <temporary-dir>/pack.json \
  --context-dir <workspace-root>/.codex/project-context
```

This produces:

```text
.codex/project-context/
├── .gitignore
├── index.md
├── state.json
└── sources/<source-id>/
    ├── summary.md
    └── excerpts.jsonl
```

Persist only the selected excerpts and compact summaries. Never store credentials, hidden reasoning, complete chat exports, or unneeded personal data. Preserve the directory-local `.gitignore` created by discovery so internal context remains untracked by default.

## Output

Lead with the answer or briefing, then report:

- sources used and skipped
- cache reuse versus refreshed retrieval
- evidence cutoff or retrieval timestamp
- important access or freshness gaps
- persisted index path

State uncertainty explicitly. Do not describe lexical ranking as embedding search, and do not claim connector scopes that were not visible at runtime.

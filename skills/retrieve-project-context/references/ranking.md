# Ranking and Deep-Trim Rules

## First-pass scoring

`rank_context.py` computes a 0–100 score:

| Component | Weight | Meaning |
| --- | ---: | --- |
| Task relevance | 60 | Supplied semantic judgment blended with lexical overlap, or lexical fallback alone |
| Source fit | 10 | Match against source purpose and query hints |
| Authority | 10 | Canonical above supporting above historical |
| Source priority | 10 | Manifest priority from 1 to 5 |
| Recency | 10 | Age relative to source freshness window |

Low-signal acknowledgements and bot-like noise receive a penalty. Near-duplicate chunks are removed. Selection applies per-source and total-character limits so one dense source cannot monopolize the result.

The algorithm is a deterministic RAG-style first pass, not embedding search. When Codex has assessed semantic relevance, provide `semantic_score` from 0 to 1. Review the output because model relevance and source authority remain judgment calls.

## Review rules

- A canonical older decision can outrank newer discussion.
- A later decision that explicitly supersedes an earlier one must preserve both the change and date.
- Corroboration is useful, but duplicated quotations are not.
- Keep contrary evidence and unresolved disagreement.
- Prefer source-diverse evidence unless the task is intentionally scoped to one source.
- Never use score to bypass permissions or manifest exclusions.

## Dense-history trigger

Use deep trim when any selected source produces:

- more than 100 messages,
- more than 40 normalized chunks,
- more than twice `source_policy.max_total_chars`, or
- substantial quoted, bot-generated, or repeated content.

## Two-pass deep trim

1. Partition content into chronological or topical windows small enough to assess coherently.
2. For each window, extract attributed decisions, requirements, actions, blockers, changes, and open questions.
3. Create one summary chunk with `is_summary: true`, stable provenance, time bounds, and `derived_from` IDs.
4. Rank window summaries against the task.
5. Expand original messages or paragraphs only for selected claims that require exact evidence.
6. Persist the summary and the smallest sufficient excerpts.

Never collapse distinct speakers into consensus. Preserve dates, owners, decision state, and links. Mark inferences as inferences.

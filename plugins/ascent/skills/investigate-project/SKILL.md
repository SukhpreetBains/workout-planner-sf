---
name: investigate-project
description: Investigate a project's context in two modes over one shared context store — map where knowledge lives, or fetch task-specific evidence from it. Use in map mode when Codex is starting work in an unfamiliar project, onboarding to an existing effort, or identifying local folders, Slack or Teams channels, SharePoint folders, stakeholders, terminology, constraints, or authoritative sources. Use in evidence mode when Codex needs ranked, bounded, cited context from known local files, Slack or Teams conversations, SharePoint folders, or other confirmed sources to answer a specific task, when long histories would otherwise consume excessive context, or when a cached briefing should be refreshed. Maintains the setup-generated workspace/.system/source-context.yaml record and the local workspace/.system/project-context/ projection used by both modes.
---

# Investigate Project

One skill, two modes, over the same shared context store. **Map mode**
answers "where does project knowledge live, and what does this project
mean?" — cheap, metadata-only, no task required. **Evidence mode**
answers a specific question by fetching, ranking, and persisting
bounded, cited content from sources the map already identified.

## Choose a mode

Ask: is there a specific task or question to answer right now?

| Situation | Mode | Read |
| --- | --- | --- |
| Starting cold in a project, onboarding, or the map is missing/stale, with no specific question yet | **Map** | `references/discover.md` |
| A decision, deliverable, or question needs cited evidence from known sources | **Evidence** | `references/retrieve.md` |

If genuinely unsure, default to map mode — it's bounded and cheap, and
evidence mode reuses whatever it produces. Evidence mode's own workflow
falls back into map mode automatically when the shared record is
missing or lacks what the task needs, so you never have to switch
documents mid-task yourself.

## Shared contract

Both modes read and write the same store:

```text
<Opportunity folder>/
└── workspace/.system/
    ├── source-context.yaml       # shared source locations from initial-setup
    └── project-context/
        ├── .gitignore
        ├── manifest.json         # generated local retrieval projection
        ├── brief.md              # compact local projection (map mode)
        ├── index.md              # task evidence index (evidence mode)
        ├── state.json            # cache/freshness state (evidence mode)
        └── sources/<source-id>/  # persisted excerpts (evidence mode)
```

Read [references/context-contract.md](references/context-contract.md)
before writing to the manifest or an evidence pack — it defines the
full manifest shape, the chunk and pack formats, and the invariants
both modes must preserve: never store credentials, message bodies, or
full connector payloads; keep source IDs stable; validate after every
write.

Read the initial-setup [project communications record
contract](../initial-setup/references/source-context.md) before
changing shared locations. `source-context.yaml` is owned by
`initial-setup`; both modes here only add to it after user
confirmation, and must preserve unknown fields and previously
confirmed locations.

## Map mode — establish or refresh the project map

Use `scripts/project_context.py` and `references/discover.md`.
Bounded, metadata-only, and interview-driven: identifies canonical
source locations (local folders, Slack/Teams channels, SharePoint
folders) and project meaning (objective, phase, terminology), records
confirmed sources in `source-context.yaml`, and generates the local
`manifest.json`/`brief.md` projection — without reading full histories,
document bodies, or message content.

## Evidence mode — fetch task-specific evidence

Use `scripts/cache_context.py`, `scripts/rank_context.py`,
`scripts/persist_context.py`, and `references/retrieve.md` (plus
`references/connector-routing.md` and `references/ranking.md`). Given
a specific task, selects accessible sources from the map, retrieves
narrowly, chunks and ranks against the task, deep-trims dense
histories, and persists a bounded evidence pack with full provenance.

## Handoff

**Map mode**: report the project communications record status, local
manifest path, confirmed source count by kind, and next recommended
action. Tell later skills to read the shared record, then `brief.md`
and `manifest.json`, before searching.

**Evidence mode**: lead with the answer or briefing, then report
sources used or skipped, cache reuse versus refreshed retrieval,
evidence cutoff, access or freshness gaps, and the persisted index
path.

Neither mode claims that content was reviewed when only its location
was resolved. Neither mode substitutes for `workspace-add`
— files a user drops in `workspace/inbox/` are that skill's job, not
this one's.

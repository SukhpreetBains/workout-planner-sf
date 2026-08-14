# SharePoint Workspace Migration Plan

Migrating the concepts of `enterprise-accelerated-delivery` (EAD) into the `ascent` skill library and a shared SharePoint folder architecture.

Status: design agreed 2026-08-13. This document records the settled decisions and the build plan.

## Relationship to other documents

- Supersedes the SharePoint Engagement folder blueprint and `99 - AI System/engagement.yaml` marker described in `plans/discovery-ai-skill-library-build-plan.md`. That plan's skill library architecture (root `skills/`, host symlinks, minimal frontmatter, host-neutral instructions) remains in force; its 21-skill catalog remains the aspirational library and is compatible with this plan.
- `enterprise-accelerated-delivery` is the concept source.
- Summit is the delivery methodology. Phase names and order come from the Summit MCP: Mobilize, Discover, Deliver, Transition, Enhance & Operate, Close.

## Core architecture

Three layers, cleanly separated:

1. **`ascent` git repo**: reusable skills, references, templates, and scripts. No live project content.
2. **SharePoint Opportunity folder** (OneDrive-synced): the engagement workspace and the only shared source of truth. Human-facing content plus a small amount of machine-managed state. No code, no databases, no per-user caches.
3. **Per-machine local caches**: deterministic, token-free, rebuildable projections of the workspace (search index, graph). Never synced.

Design rule that governs everything: **the SharePoint folder is the source of truth; every local cache is a deterministic, token-free function of its contents.** Anything that costs tokens produces a file in the folder. Anything derived from the folder is free to rebuild and lives outside it.

## Workspace folder structure

```text
<Account>/                          # existing client SharePoint folder, never renamed
  Client Culture/                   # cross-engagement client knowledge
    Client Role Map/
    Preferences/
  <Opportunity>/                    # one per engagement; the workspace root
    Config/
      project.md                    # engagement profile (replaces engagement.yaml marker)
      summit-phase.md               # current Summit phase; drives skill behavior
      glossary.yaml                 # canonical term to client-synonym groups (Phase 2)
    Content Inbox/
      Transcripts/
      Threads/
      Client Docs/
    Agent Inbox/
      In Progress/
      Ready for Review/
      source-context.yaml           # project communications record (existing contract)
      processing-log.yaml           # content hash to processed-status ledger
    Deliverables/
      01 - Mobilize/
      02 - Discover/
      03 - Deliver/
      04 - Transition/
```

Notes:

- Content Inbox is per-Opportunity. The earlier idea of a root-level `Agent Gathered/` area is dropped.
- Deliverables folders use Summit phase order with numeric prefixes so SharePoint sorts them by lifecycle. `05 - Enhance & Operate` and `06 - Close` are added only when an engagement reaches them.
- Approved trackers (see below) live inside the Deliverables phase folders as living deliverables.
- Skills locate the workspace root by walking upward from the current directory until they find `Config/project.md`.
- `initial-setup` recommends "Always keep on this device" for Content Inbox so local scripts never hit OneDrive online-only placeholders.

## Agent permission guardrail (v2)

Written to the Opportunity root `AGENTS.md` by `initial-setup` from a static template. Applies to every agent session on every host.

| Location | Agent permission |
|---|---|
| `Agent Inbox/` | Full read-write. All iteration and work-in-progress happens here. |
| `Content Inbox/Threads/` | Create-only. Add exports; never modify, move, or delete existing files. |
| `Content Inbox/Transcripts/`, `Content Inbox/Client Docs/` | Read-only. |
| `Deliverables/` | Create-only, and only files whose name ends in `_AGENT_DRAFT` (before the extension). Never edit, rename, move, or delete anything, including a draft the agent created earlier. |
| `Config/` | Agent-writable, but every create or update is gated behind explicit human approval in the current conversation. No silent writes. |

The filesystem is the workflow engine: nothing becomes approved truth unless a human moves or renames it into place.

## Draft lifecycle (`_AGENT_DRAFT`)

1. Agent iterates in `Agent Inbox/In Progress/`.
2. When review-ready, agent creates `Deliverables/<phase>/<Name>_AGENT_DRAFT.<ext>`. For updates to an existing deliverable or tracker, the draft sits next to the approved file and opens with a change summary: what changed, why, with citations.
3. Human reviews and edits. Approval is renaming to drop the suffix (new deliverable) or merging into the approved file (update), then deleting the draft.
4. Agents never touch a placed draft. A revision after feedback is a new file with a `_v2` suffix (`<Name>_AGENT_DRAFT_v2.<ext>`). Skills flag stale same-named drafts to the human instead of working around them.
5. Generated reports state in their header which sources they were built from (count, dates, hash manifest reference) so reviewers can spot staleness.

`Agent Inbox/Ready for Review/` holds non-deliverable review items: extraction change sets, contradiction reports, open questions, and anything needing a human decision that is not itself a client-facing artifact.

## Trackers

Structured project data lives as markdown/YAML trackers inside the Deliverables phase folders. Excel views are generated on demand as deliverables, never the source of truth (EAD's whole-file xlsx rewrite model conflicts fatally with SharePoint co-authoring and sync).

Entity ID scheme, carried over from EAD verbatim:

| Prefix | Entity |
|---|---|
| `STK-` | Stakeholder |
| `STR-` | Stakeholder relationship |
| `PAIN-` | Pain point |
| `SYS-` | System |
| `DEC-` | Decision |
| `RSK-` | Risk |
| `CST-` | Constraint |
| `ASM-` | Assumption |
| `QST-` | Open question |
| `OBJ-` | Objective / outcome |
| `REQ-` | Requirement |

Every tracker entry has a stable `id` and typed link fields referencing other IDs (for example `addresses: [OBJ-003]`). IDs are permanent anchors for citations and are the substrate the Phase 2 graph is built on. This is locked from day one because retrofitting IDs is not practical.

## Intake flow

```text
Content Inbox (new transcript / thread / doc)
      |
      v
Agent reads source + current trackers in Deliverables
      |
      v
Agent Inbox/In Progress/          working extraction
      |
      v
Agent Inbox/Ready for Review/     one change-set file per source:
      |                           new facts, proposed tracker changes,
      |                           contradictions, each with citation
      v
Human reviews; approved tracker changes surface as _AGENT_DRAFT
tracker updates in Deliverables; human merges and deletes drafts
      |
      v
Agent Inbox/processing-log.yaml   source hash -> processed, proposal ref, date
```

Three EAD ideas preserved as skill instructions plus light validation, not machinery:

1. **Closed action set.** Every extracted item is exactly one of: new entity, update to existing entity, contradiction, evidence attachment. Anything else is out of contract.
2. **Citation discipline.** Every fact carries source file plus location (timestamp for transcripts, permalink for threads, page or section for documents), anchored to entity IDs.
3. **Idempotence via the processing log.** Content-hash keyed. Any future session, on any machine, can tell what has been handled. Files are never moved out of Content Inbox (the guardrail forbids it; provenance is better this way).

The scheduled import run (existing `retrieve-project-context` pattern, runs locally on a synced machine, scheduled or human-triggered) drives this flow.

## Retrieval and caches

**Phase 1: none.** Agents read trackers and relevant sources directly. Early-engagement corpora fit in context. `retrieve-project-context` covers import-time ranking and bounded summaries.

**Phase 2: per-machine rebuildable cache.** Built entirely by script, zero tokens, seconds to rebuild:

```text
SharePoint (shared truth)                 Local machine (rebuildable, never synced)
Content Inbox/            --+
Deliverables/ trackers    --+--> indexer --> ~/.ascent/<account>/<opportunity>/
Agent Inbox/ items        --+                  search.db   (SQLite FTS5 BM25)
Config/glossary.yaml      ----> expansion      graph.json  (typed entity edges)
processing-log.yaml       ----> freshness      manifest.json (content hashes)
```

- Freshness is content-hash based (shared scheme with the processing log). mtime is never trusted; OneDrive rewrites it.
- Caches cannot diverge in a harmful way: no cache writes back to truth. Two users' caches differ only by sync lag or build lag, both detectable via manifest-versus-folder hash comparison (`status` command) and self-healing via rebuild.
- No shared cache on SharePoint. Every machine builds its own. (A publish-snapshot pattern was considered and rejected as unnecessary: builds are token-free and take seconds.)
- SQLite never lives on, and is never opened from, a synced path.
- A query tool (ported from EAD's `query.py` command set: `shortlist`, `entities`, `related`, `evidence`, `status`) is what skills call instead of re-reading the corpus.
- The graph powers the highest-value derived views: traceability audit (every commitment landed somewhere, orphans flagged both directions), coverage gaps (pain points no objective addresses), stakeholder map, tensions. Views render as `_AGENT_DRAFT` deliverables or Ready for Review reports.

Phase 1 ships one Phase 2 stub: the scheduled import run calls the indexer if present and no-ops otherwise, so adding the index later requires no change to the scheduled job.

## Naming conventions (EAD term renames)

| EAD term | Replacement |
|---|---|
| knowledge hub | the Opportunity folder / engagement workspace |
| registers | trackers, named for what they hold (Stakeholder Tracker, RAID Log) |
| lanes / lane cards | entity types / extraction schemas |
| proposals | review items (matching `Ready for Review/`) |
| mirrors / projections | agent accessible data (local, never synced) |
| derived state refresh | rebuild |
| gate | Summit phases |
| overlays | capability / industry |
| playbook / stage / phase | Summit phase names everywhere, driven by `Config/summit-phase.md` |

## EAD skill dispositions

| EAD skill | Disposition |
|---|---|
| `setup` | Superseded by `initial-setup` (update it: guardrail v2, `Config/`, numbered Deliverables folders). |
| `process-inbox` | Lean rebuild as the intake skill (closed action set, citations, processing log). Do not port `intake_engine.py`. |
| `process-session` | Fold into intake / future `discovery-session` per the skill-library plan; compatibility name optional. |
| `review` | Largely replaced by the `_AGENT_DRAFT` + Ready for Review human workflow. Optional light helper skill later. |
| `synthesize` | Port; adapt paths to workspace layout. |
| `analyze` | Port the concept; analysis outputs are drafts/review items. AnalysisCore JSON optional, adopt only if two skills need the contract. |
| `conflict-check` | Port. |
| `hub-audit` | Port as readiness-check (phase-gate readiness against Summit criteria; never self-certifies a gate). |
| `prep-workshop` | Defer; future `discovery-session` prepare mode. |
| `diagram-process` | Port as-is. |
| `manage-backlog` | Port; backlog source of truth becomes a tracker, Excel workbook becomes a generated deliverable. |
| `compose-deliverable` | Port; reads trackers and drafts, writes `_AGENT_DRAFT` outputs. |
| `generate-template`, `salesforce-demo-data` | Optional specialty; port on demand. |
| `author-overlay-package` + overlays | Rename capability/industry packs; port when the second engagement type needs it. |
| `docx` / `excel` / `pdf` / `pptx` tools | Port the scripts the retained skills need; reconcile with already-installed skills (`convert-documents-to-markdown`, `pdf`, `slalom-powerpoint-template`) to avoid duplicates. |

EAD scripts worth carrying: `search_index_lib.py` and `query.py` (Phase 2, mostly intact, new input walkers), the docx/excel converter modules (Phase 1, as needed by retained skills). Everything else (write contract, ontology registry, mirrors, graph builder, staleness checks, lock retry) is replaced by simpler equivalents or dropped.

## Build phases

### Phase 1: foundation (the human workflow made reliable)

- [ ] Update `initial-setup`: guardrail v2 template, `Config/` creation, numbered Summit-ordered Deliverables folders, Files On-Demand guidance, workspace-root resolution via `Config/project.md`.
- [ ] Define tracker templates with the ID scheme and typed link fields; document the tracker format contract.
- [ ] Build the intake skill: closed action set, citation format, change-set file format, processing-log updates.
- [ ] Document the `_AGENT_DRAFT` lifecycle and Config approval gate in the `AGENTS.md` template and skill instructions.
- [ ] Port core work skills: `synthesize`, `conflict-check`, `diagram-process`, `compose-deliverable`, `manage-backlog` (tracker-backed), readiness-check.
- [ ] Port required file-format scripts; reconcile with installed skills.
- [ ] Wire the scheduled import run: import, extract, change set, processing log, indexer stub (no-op).
- [ ] Tests: workspace-root resolution (nested invocation, spaces in names, missing/duplicate Config), guardrail template correctness, processing-log idempotence, tracker template validation.

### Phase 2: scale layer (build when a real engagement outgrows direct reading)

Trigger signals: sessions re-reading the same transcripts, context budgets strained, missed cross-references, roughly 30+ sources or 100+ tracker entities.

- [ ] Port `search_index_lib.py` + query tool; new input walkers over the workspace layout; index at `~/.ascent/<account>/<opportunity>/`.
- [ ] Lean graph builder over YAML tracker link fields; `graph.json` + manifest.
- [ ] Glossary: `Config/glossary.yaml` format, agent-proposed additions through the Config approval gate, query expansion.
- [ ] Derived views: traceability audit, coverage gaps, stakeholder map, tensions, rendered as drafts/review items.
- [ ] Turn the indexer stub live in the scheduled import run.

## Rejected alternatives (recorded so they are not relitigated)

- Excel workbooks as structured-data source of truth: whole-file rewrite conflicts with SharePoint sync and co-authoring; single-writer discipline is unenforceable.
- Root-level shared `Agent Gathered/` content area: content is engagement-specific; per-Opportunity Content Inbox retained.
- Porting `intake_engine.py` / `write_registers.py` / ontology machinery: built around xlsx registers, mirror projections, mtime freshness, and git-tree assumptions that do not survive SharePoint. Concepts retained; code not.
- Shared cache snapshot published to SharePoint: workable (build locally, publish closed artifact, consumers copy before opening) but unnecessary since builds are token-free and fast; adds a designated-user single point of failure.
- Append-only change log with regenerated trackers: viable growth path if tracker churn under full-copy drafts becomes painful; not built initially.

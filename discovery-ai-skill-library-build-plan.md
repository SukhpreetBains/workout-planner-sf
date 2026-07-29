# Discovery AI Skill Library — Implementation Handoff Plan

## Purpose

This document is the build handoff for another agent. It translates the agreed Discovery AI design into an implementation plan for the `ascent` repository.

The implementation should create a tool-agnostic skill library modeled on the symlink architecture in:

`/Users/calvinokeefe/Desktop/Ascent/slalom-static-ascent-skills-training/salesforce-accelerated-engineering`

The target repository is:

`/Users/calvinokeefe/Desktop/Ascent/ascent`

The business requirements come from slide 8 of:

`/Users/calvinokeefe/Desktop/Ascent/Docs/ASCENT Scaled PoC.pptx`

This plan is self-contained. Do not require the builder to reconstruct decisions from prior conversation.

---

## Instructions to the implementing agent

1. Read the target repository's `AGENTS.md` before changing files.
2. Ask whether the user wants a new branch before implementation. Suggested names:
   - `feature/discovery-ai-skill-library`
   - `refactor/skill-library-architecture`
3. Inspect `git status` before editing. The repository currently contains user changes; preserve them.
4. Do not pull, rebase, overwrite, delete, or clean existing work without explicit approval.
5. Implement in phases. Keep the repository working at the end of every phase.
6. Use the reference repository for architectural conventions, not Salesforce-specific business requirements.
7. Do not create a root `knowledge-hub/` in the final architecture.
8. Do not invent Mobilize or Discovery exit criteria. The source slide shows gates but does not define their rules.
9. Do not create a new process-design skill in this implementation. Process design is explicitly deferred.
10. Do not rewrite `analyze-org` as process analysis. It is a Salesforce metadata architecture mapper.

---

## Confirmed design decisions

### 1. The repository is a reusable skill library

The Git repository contains:

- reusable skills;
- references;
- templates;
- skill-specific scripts;
- shared tools when necessary;
- installation and contributor guidance.

It does not contain live project documents or a sample project `knowledge-hub`.

### 2. SharePoint is the project workspace

Each client Account has a SharePoint folder. Each Engagement has a folder beneath the Account.

The Engagement folder itself is the project root. There is no nested folder named `knowledge-hub`.

### 3. The skill library uses a single source of truth

Copy the architecture used by the reference repository:

```text
skills/                   # authoritative skill source
.claude/skills  -> ../skills
.codex/skills   -> ../skills
.cursor/skills  -> ../skills
.github/skills  -> ../skills
```

The symlinks must be relative and committed as Git symlinks.

### 4. Skills use progressive disclosure

Every skill begins with:

```text
skills/<skill-name>/SKILL.md
```

Add these only when justified:

```text
references/   # detailed guidance loaded on demand
templates/    # reusable project deliverables
scripts/      # deterministic automation owned by the skill
```

Do not create schemas preemptively. Add a schema only when two skills require a strict machine-readable contract that cannot be handled safely through a simple documented format.

### 5. Skill frontmatter stays minimal

Use:

```yaml
---
name: <kebab-case-name>
description: <what the skill does, when to use it, and an important exclusion>
---
```

The directory name and `name` must match.

The description is the trigger contract. It must distinguish the skill from adjacent skills.

### 6. Skills are host-neutral

Skills may run under Claude Code, Codex, Cursor, or GitHub Copilot.

Instructions must:

- refer generically to the active agent's user-input mechanism;
- fall back to plain chat;
- avoid assuming one host's tool names;
- call other skills by skill name rather than by one platform-specific path.

### 7. Numbered project folders are intentional

Numbers are lifecycle sort keys, not inherited legacy names. Number only the Engagement root folders.

---

## Target repository structure

```text
ascent/
├── AGENTS.md
├── README.md
├── WORKFLOW.md
├── skills/
│   ├── setup/
│   ├── sales-handoff/
│   ├── mobilize/
│   ├── stakeholder-analysis/
│   ├── discovery-session/
│   ├── discovery-survey/
│   ├── analyze-org/
│   ├── architecture/
│   ├── capability-mapping/
│   ├── business-case/
│   ├── product-planning/
│   ├── ai-strategy/
│   ├── discovery/
│   ├── persona-journey/
│   ├── risk-management/
│   ├── governance-operating-model/
│   ├── change-strategy/
│   ├── delivery-planning/
│   ├── devops-security/
│   ├── test-strategy/
│   ├── data-migration-strategy/
│   └── <retained support and specialty skills>/
├── tools/
├── .claude/
│   └── skills -> ../skills
├── .codex/
│   └── skills -> ../skills
├── .cursor/
│   └── skills -> ../skills
├── .github/
│   └── skills -> ../skills
└── .agents/
    ├── skills -> ../skills       # temporary compatibility symlink
    ├── scripts/
    ├── references/
    └── <existing runtime assets>
```

Do not nest skills by phase. Keep skill discovery flat and encode lifecycle behavior in the orchestrator skills.

### Compatibility symlink

The current repository has extensive references to `.agents/skills/...`.

During migration:

1. Move the authoritative directory from `.agents/skills/` to root `skills/`.
2. Replace `.agents/skills` with a relative symlink to `../skills`.
3. Preserve the compatibility symlink until active references have been migrated and verified.

This gives one source of truth immediately without forcing every path migration into the first commit.

### Catalog authority

`skills/*/SKILL.md` is the source of truth for skill discovery.

If `skills-catalog.yaml` remains:

- update paths to `skills/<name>/SKILL.md`;
- mark it as generated or compatibility metadata;
- do not make it a second independently maintained source of truth.

---

## SharePoint Engagement folder blueprint

`setup` should preview and create this structure directly beneath the Engagement folder:

```text
<Account>/
  <Engagement>/
    01 - Sales Handoff/
    02 - Engagement Setup/
    03 - Discovery Research/
    04 - Current State/
    05 - Future State/
    06 - Product & Roadmap/
    07 - Delivery Readiness/
    08 - Governance & Change/
    09 - Final Deliverables/
    90 - Structured Data/
    99 - AI System/
```

### Folder meanings

| Folder | Purpose |
|---|---|
| `01 - Sales Handoff` | MSA, SOW, client context, RFP responses, reusable IP, sales calls, and ways-of-working inputs |
| `02 - Engagement Setup` | Engagement profile, scope, charter, business case, KPIs, Mobilize and Discovery plans |
| `03 - Discovery Research` | Interviews, workshops, ride-alongs, surveys, personas, transcripts, notes, and raw evidence |
| `04 - Current State` | Current organizational, process, stakeholder, capability, solution, technical, DevOps, and AI views |
| `05 - Future State` | Target journeys, capabilities, solution/technical architecture, data/integration plans, and AI strategy |
| `06 - Product & Roadmap` | Epics, features, stories, MVP definition, priorities, and roadmap |
| `07 - Delivery Readiness` | Project plan, timeline, milestones, DevOps/security, testing, and data migration |
| `08 - Governance & Change` | Governance, operating model, RACI, change strategy, and stakeholder engagement |
| `09 - Final Deliverables` | Approved client-facing deliverables only |
| `90 - Structured Data` | Inspectable project facts, evidence, requirements, risks, decisions, traceability, and registers |
| `99 - AI System` | Engagement marker, workflow status, manifests, and machine-managed shared state |

### Engagement marker

`setup` should create:

```text
99 - AI System/engagement.yaml
```

Keep the first version lean:

```yaml
account: ""
engagement: ""
engagement_type: ""
technology_focus: []
industry: ""
sharepoint_url: ""
workspace_version: 1
created_at: ""
```

Do not store credentials or a machine-specific absolute local path in the shared marker.

Later skills should locate the Engagement root by walking upward from the current directory until they find `99 - AI System/engagement.yaml`.

---

## Installation and symlink behavior

Model the README and installation guidance on the reference library.

### Supported hosts

| Host | Global target | Project-local target |
|---|---|---|
| Claude Code | `~/.claude/skills` | `<PROJECT_ROOT>/.claude/skills` |
| Codex | `~/.codex/skills` | `<PROJECT_ROOT>/.codex/skills` |
| Cursor | `~/.cursor/skills` | `<PROJECT_ROOT>/.cursor/skills` |
| GitHub Copilot | `~/.github/skills` | `<PROJECT_ROOT>/.github/skills` |

### Recommended default

Recommend global installation for this library because Engagement roots are SharePoint/OneDrive-synced folders. Machine-specific project-local symlinks should not normally be synchronized into SharePoint.

Still document project-local installation for users who need version isolation.

### Installation safety

The installer guidance must:

1. Detect the active host or ask.
2. Ask global versus project-local.
3. Stop if the target `skills` path is a real, non-empty directory.
4. Replace an existing symlink only after showing its current target.
5. Create a symlink on macOS/Linux.
6. Use a directory junction or documented copy fallback on Windows.
7. Verify the link resolves and list discovered skill names.

Do not add hooks in the first implementation merely because the reference repository has hooks. The requested reuse is the skill symlink architecture. Hooks remain a future, separately approved capability.

---

## Skill composition model

### Phase coordinators

```text
setup
  ↓
sales-handoff
  ↓
mobilize
  ↓
user-approved Mobilize completion
  ↓
discovery
  ↓
user-approved Discovery completion
```

`mobilize` and `discovery` coordinate specialist skills. They do not absorb specialist methods.

### Shared support engines from the existing repository

Retain and compose these where useful:

| Existing skill | Intended role |
|---|---|
| `analyze` | Shared structured-analysis engine |
| `synthesize` | Shared narrative-synthesis engine |
| `process-inbox` | Shared file intake and evidence routing |
| `review` | Human approval and canonical write workflow |
| `conflict-check` | Contradiction detection |
| `hub-audit` | Quality and readiness checks after its path model is updated |
| `compose-deliverable` | Template-based final artifact generation |
| `manage-backlog` | Backlog operations beneath `product-planning` |
| `pdf`, `docx`, `pptx`, `excel` | File-format tools |
| `author-overlay-package` | Industry/capability reference packs and sample backlogs |
| `diagram-process` | Optional retained support; new process-design work is deferred |

Keep `generate-template` and `salesforce-demo-data` as optional specialty skills unless the user asks to remove them.

### Consolidations

- Fold the user-facing behavior of `prep-workshop` and `process-session` into the two modes of `discovery-session`.
- Keep compatibility wrappers initially if other skills still call the old names.
- Put `manage-backlog` beneath `product-planning`; do not duplicate workbook logic.
- Put `hub-audit` beneath phase coordination; do not invent gate rules it does not have.

---

## Primary skill specifications

The primary library contains 21 agreed workflow and specialist skills, including `analyze-org`.

### 1. `setup`

**Purpose:** conversationally initialize an engagement, find or create the SharePoint Account folder, create the Engagement folder, create the agreed subfolders, and help the user make the Engagement available locally through OneDrive.

**Required behavior:**

1. Collect:
   - Account/client name;
   - Engagement name;
   - Engagement type;
   - technology/capability focus;
   - industry;
   - start/end dates;
   - delivery lead/team;
   - client sponsor;
   - known objectives;
   - current phase.
2. Determine the SharePoint site and document library.
3. Find the Account folder or obtain approval to create it.
4. Propose and confirm the Engagement folder name.
5. Preview the folder blueprint before creation.
6. Create only missing folders.
7. Support:
   - connected mode when a SharePoint connector is available;
   - guided mode when the user must perform browser actions.
8. Walk the user through OneDrive synchronization on macOS or Windows.
9. Verify the resulting local Engagement folder and read/write access.
10. Create `99 - AI System/engagement.yaml`.
11. Tell the user to open the locally synced Engagement folder as the working directory for later skills.
12. Be resumable and idempotent.

**Initial package:**

```text
skills/setup/
  SKILL.md
  references/
    engagement-intake.md
    sharepoint-workspace.md
    local-sync-macos.md
    local-sync-windows.md
  templates/
    engagement.yaml
```

**Boundary:** no source-document analysis and no discovery deliverables.

### 2. `sales-handoff`

**Purpose:** turn the Sales Delivery Handoff materials into an organized, traceable brief for Mobilize.

**Slide-defined inputs:**

- MSA;
- SOW;
- client context;
- past RFP response;
- reusable IP;
- call logs;
- ways of working.

**Required behavior:**

- preserve source documents unchanged;
- identify missing inputs, duplicates, and superseded versions;
- distinguish contractual commitments from context and reusable examples;
- extract scope, exclusions, assumptions, dependencies, deliverables, dates, stakeholders, and open questions;
- create a Sales Handoff Brief;
- report whether Mobilize has enough information to begin.

**Initial package:**

```text
skills/sales-handoff/
  SKILL.md
  references/
    handoff-inputs.md
  templates/
    sales-handoff-brief.md
```

**Output:**

```text
01 - Sales Handoff/Sales Handoff Brief.md
```

**Reuse:** `process-inbox`, `synthesize`, `conflict-check`, and file-format skills.

### 3. `mobilize`

**Purpose:** coordinate the Mobilize phase and own the Project Charter.

**Important interpretation:** the slide's “Prompt Library for Knowledge Hub” means this reusable skill library. It is not a Mobilize activity or project deliverable. Industry guides and sample backlogs are reference packs selected during setup.

**Mobilize activities reference must include:**

- collect Sales Delivery Handoff inputs;
- collect ride-along observations;
- collect Hubbl or other platform assessment output;
- collect system landscape, architecture diagram, and ERD inputs;
- collect DevOps information;
- collect relationship maps and existing stakeholder analysis;
- confirm ways of working;
- run asynchronous surveys.

**Mobilize deliverables reference must include:**

- business case and KPIs;
- project charter;
- current-state processes and journeys;
- current solution architecture;
- current technical architecture;
- capability map;
- high-level epics and features;
- current technical landscape, including DevOps and AI;
- stakeholder analysis;
- AI strategy.

**Initial package:**

```text
skills/mobilize/
  SKILL.md
  references/
    mobilize-activities.md
    mobilize-deliverables.md
  templates/
    project-charter.md
```

**Outputs:**

```text
02 - Engagement Setup/Project Charter.md
02 - Engagement Setup/Mobilize Plan.md
02 - Engagement Setup/Mobilize Status.md
```

**Boundary:** coordinates specialist skills; it does not author their specialist deliverables.

**Exit handling:** show deliverable status and ask the user whether to proceed. Do not invent automatic exit criteria.

### 4. `stakeholder-analysis`

**Purpose:** create stakeholder analysis, relationship mapping, coverage tracking, and an engagement plan.

**Initial package:**

```text
skills/stakeholder-analysis/
  SKILL.md
  references/
    stakeholder-analysis-guidance.md
    relationship-mapping-guidance.md
  templates/
    stakeholder-analysis.md
    stakeholder-engagement-plan.md
```

**Outputs:**

```text
04 - Current State/Stakeholder Analysis.md
04 - Current State/Stakeholder Relationship Map.md
03 - Discovery Research/Stakeholder Engagement Plan.md
```

**Boundary:** no governance model, final RACI, or change strategy.

### 5. `discovery-session`

**Purpose:** prepare and process one interview, workshop, or ride-along.

**Modes:**

- `prepare`;
- `process`.

**Initial package:**

```text
skills/discovery-session/
  SKILL.md
  references/
    session-questioning-guidance.md
    evidence-capture-guidance.md
  templates/
    interview-plan.md
    workshop-plan.md
    ride-along-plan.md
    session-notes.md
```

**Output pattern:**

```text
03 - Discovery Research/<YYYY-MM-DD - Session Name>/
  Session Plan.md
  Session Notes.md
  <original transcript or notes>
```

**Reuse:** consolidate `prep-workshop` and `process-session`.

### 6. `discovery-survey`

**Purpose:** design asynchronous discovery surveys and analyze exported responses.

**Modes:**

- `design`;
- `analyze`.

**Initial package:**

```text
skills/discovery-survey/
  SKILL.md
  references/
    survey-design-guidance.md
    survey-analysis-guidance.md
  templates/
    survey-plan.md
    survey-questionnaire.md
    survey-findings.md
```

**Boundary:** no automatic survey-platform distribution in the first version.

### 7. `analyze-org`

**Purpose:** map Salesforce org metadata into a persistent architecture map.

**Source:** port the complete existing package from:

```text
/Users/calvinokeefe/Desktop/Ascent/slalom-static-ascent-skills-training/
  salesforce-accelerated-engineering/skills/analyze-org/
```

Preserve:

- `SKILL.md`;
- `manifest/package.xml`;
- `references/`;
- `scripts/`;
- script tests and package files.

**Critical correction:** this skill does not analyze business processes. It clusters and documents Salesforce metadata architecture.

**Required adaptation:**

- when an Engagement marker exists, write the map to:

```text
04 - Current State/Architecture/Salesforce Org Map/
  architecture.md
  vocabulary.md
  features/
  .dependency/
```

- otherwise retain its existing project-root fallback for ordinary Salesforce projects;
- make the output root configurable rather than duplicating skill logic;
- update reference links and bootstrap commands for the new root `skills/` layout;
- keep the existing deterministic dependency-graph generator;
- preserve manual notes and user-owned vocabulary on refresh.

**Relationship:** `architecture` consumes the map when Salesforce is in scope.

### 8. `architecture`

**Purpose:** own current- and future-state solution and technical architecture across technologies.

**Modes:**

- `current-state`;
- `future-state`.

**Current-state behavior:**

- use existing architecture, ERD, Hubbl, platform metadata, DevOps, integration, and system inventory evidence;
- invoke `analyze-org` for Salesforce-specific metadata mapping;
- create current solution architecture;
- create current technical architecture;
- create system/integration inventory;
- identify gaps and assumptions.

**Future-state behavior:**

- perform solution design;
- create future solution architecture;
- create future technical architecture;
- define data and integration direction;
- connect decisions to requirements, constraints, risks, and capabilities.

**Initial package:**

```text
skills/architecture/
  SKILL.md
  references/
    current-solution-architecture-guidance.md
    current-technical-architecture-guidance.md
    system-landscape-and-erd-guidance.md
    future-solution-architecture-guidance.md
    future-technical-architecture-guidance.md
    data-and-integration-planning.md
  templates/
    current-solution-architecture.md
    current-technical-architecture.md
    system-and-integration-inventory.md
    future-solution-architecture.md
    future-technical-architecture.md
```

**Boundary:** current-state architecture records DevOps and AI context but does not own their strategies.

### 9. `capability-mapping`

**Purpose:** create current and target capability maps.

**Modes:**

- `current-state`;
- `target-state`.

**Initial package:**

```text
skills/capability-mapping/
  SKILL.md
  references/
    capability-mapping-guidance.md
  templates/
    capability-map.md
```

**Outputs:**

```text
04 - Current State/Capability Map.md
05 - Future State/Target Capability Map.md
```

### 10. `business-case`

**Purpose:** define and refine the business case, KPI baselines, targets, benefit assumptions, and evidence gaps.

**Modes:**

- `baseline`;
- `refine`.

**Initial package:**

```text
skills/business-case/
  SKILL.md
  references/
    business-case-and-kpi-guidance.md
  templates/
    business-case-and-kpis.md
```

**Output:**

```text
02 - Engagement Setup/Business Case and KPIs.md
```

### 11. `product-planning`

**Purpose:** move from high-level epics/features through backlog, MVP, priorities, and roadmap.

**Modes:**

- `high-level`;
- `backlog`;
- `mvp`;
- `roadmap`.

**Initial package:**

```text
skills/product-planning/
  SKILL.md
  references/
    epic-feature-story-guidance.md
    prioritization-and-mvp-guidance.md
    roadmap-guidance.md
  templates/
    product-backlog.md
    mvp-definition.md
    product-roadmap.md
```

**Reuse:** `manage-backlog`, `analyze`, `excel`.

### 12. `ai-strategy`

**Purpose:** assess the current AI landscape and define future AI strategy.

**Modes:**

- `assess`;
- `strategy`.

**Initial package:**

```text
skills/ai-strategy/
  SKILL.md
  references/
    ai-use-case-guidance.md
    responsible-ai-guidance.md
  templates/
    current-ai-landscape.md
    ai-strategy.md
```

### 13. `discovery`

**Purpose:** coordinate Discovery activities, specialist outputs, validation, and the user-approved exit decision.

**Discovery activities reference must include:**

- targeted stakeholder interviews and workshops;
- user/persona definition;
- journey mapping;
- future-state process design;
- future-state architecture design;
- solution design;
- data and integration planning;
- MVP definition;
- product-roadmap development;
- risk assessment;
- governance validation.

**Discovery deliverables reference must include:**

- business case, KPIs, and charter;
- to-be processes and journeys;
- epics, features, and stories;
- solution architecture;
- technical architecture;
- governance, operating model, and RACI;
- capability map;
- product roadmap and priorities;
- timeline and milestones;
- change strategy and stakeholder analysis;
- project plan;
- DevOps framework, security, and Infosec;
- test plan and strategy;
- AI strategy;
- data migration strategy.

**Initial package:**

```text
skills/discovery/
  SKILL.md
  references/
    discovery-activities.md
    discovery-deliverables.md
  templates/
    discovery-plan.md
    discovery-deliverable-checklist.md
```

**Outputs:**

```text
02 - Engagement Setup/Discovery Plan.md
02 - Engagement Setup/Discovery Deliverable Checklist.md
```

**Deferred requirement:** mark future-state operational process design as deferred/manual in the first version. Do not claim `analyze-org` covers it. `persona-journey` covers human journeys only.

**Exit handling:** show completion and validation status, then ask the user to proceed or hold. Do not invent gate thresholds.

### 14. `persona-journey`

**Purpose:** define users/personas and map current or future human experiences and journeys.

**Modes:**

- `current`;
- `future`.

**Initial package:**

```text
skills/persona-journey/
  SKILL.md
  references/
    persona-and-journey-guidance.md
  templates/
    persona-profile.md
    journey-map.md
```

**Boundary:** no internal operational process design.

### 15. `risk-management`

**Purpose:** identify, assess, assign, monitor, and report project and solution risks.

**Initial package:**

```text
skills/risk-management/
  SKILL.md
  references/
    risk-assessment-guidance.md
  templates/
    risk-assessment.md
```

**Reuse:** current intake/review pipeline, RAID artifacts, `conflict-check`, and `hub-audit`.

### 16. `governance-operating-model`

**Purpose:** create governance, decision rights, operating model, and RACI; validate them during Discovery.

**Initial package:**

```text
skills/governance-operating-model/
  SKILL.md
  references/
    governance-and-raci-guidance.md
  templates/
    governance-operating-model.md
    raci.md
```

### 17. `change-strategy`

**Purpose:** assess change impacts and create the stakeholder engagement, communications, adoption, and readiness strategy.

**Initial package:**

```text
skills/change-strategy/
  SKILL.md
  references/
    change-impact-and-adoption-guidance.md
  templates/
    change-strategy.md
```

### 18. `delivery-planning`

**Purpose:** create the project plan, timeline, milestones, dependencies, and resourcing assumptions.

**Initial package:**

```text
skills/delivery-planning/
  SKILL.md
  references/
    delivery-planning-guidance.md
  templates/
    project-plan.md
    timeline-and-milestones.md
```

### 19. `devops-security`

**Purpose:** define the future DevOps framework, environment approach, release controls, security, and Infosec direction.

**Initial package:**

```text
skills/devops-security/
  SKILL.md
  references/
    devops-and-security-guidance.md
  templates/
    devops-security-framework.md
```

### 20. `test-strategy`

**Purpose:** create the test plan and strategy, including levels, ownership, environments, traceability, automation direction, and entry/exit conditions.

**Initial package:**

```text
skills/test-strategy/
  SKILL.md
  references/
    test-strategy-guidance.md
  templates/
    test-strategy.md
```

Reuse the existing Test Cases workbook through `compose-deliverable` when appropriate; do not duplicate it unless ownership is intentionally migrated.

### 21. `data-migration-strategy`

**Purpose:** define migration scope, sources, targets, mapping, data quality, waves, reconciliation, cutover, rollback, and ownership.

**Initial package:**

```text
skills/data-migration-strategy/
  SKILL.md
  references/
    data-migration-guidance.md
  templates/
    data-migration-strategy.md
```

Reuse the existing Deployment Cutover workbook when appropriate.

---

## Phase coordination

### Mobilize

```text
mobilize
├── sales-handoff
├── stakeholder-analysis
├── discovery-session
├── discovery-survey
├── analyze-org                      # Salesforce only
├── architecture: current-state
├── capability-mapping: current-state
├── business-case: baseline
├── product-planning: high-level
└── ai-strategy: assess
```

### Discovery

```text
discovery
├── discovery-session
├── discovery-survey
├── persona-journey
├── architecture: future-state
├── capability-mapping: target-state
├── business-case: refine
├── product-planning: backlog / mvp / roadmap
├── risk-management
├── governance-operating-model
├── change-strategy
├── delivery-planning
├── devops-security
├── test-strategy
├── ai-strategy: strategy
└── data-migration-strategy
```

### Coordination rules

1. Coordinators determine applicability; not every engagement needs every specialist output.
2. Coordinators show the proposed plan before invoking state-changing work.
3. Specialist skills own their deliverables and validation.
4. Coordinators track paths, status, gaps, owners, and validation state.
5. A deliverable may be:
   - not applicable;
   - not started;
   - in progress;
   - ready for validation;
   - validated;
   - blocked.
6. Coordinators do not silently mark work validated.
7. The user owns phase transition decisions until formal exit criteria are supplied.

---

## Existing repository migration

### Root `knowledge-hub/` removal

The current root `knowledge-hub/` contains:

- blank register workbooks;
- backlog template workbook;
- project Markdown templates;
- shared-state starter files;
- folder scaffolding.

Before removing the directory:

1. Inventory every tracked file.
2. Move reusable blank workbooks and deliverable assets under the skill that owns them or the existing shared deliverable-template library.
3. Move reusable project starter documents into the appropriate skill's `templates/`.
4. Move extraction policy, glossary, backlog profile, and similar reusable defaults under the support skill that owns them.
5. Update scripts so they resolve the Engagement root through `99 - AI System/engagement.yaml`.
6. Update active documentation and tests.
7. Verify no reusable asset remains solely under `knowledge-hub/`.
8. Remove the root directory in a dedicated, reviewable commit.

Do not delete the directory first and reconstruct assets afterward.

### Recommended asset ownership

| Current asset | New owner |
|---|---|
| Project Overview / Phase Context / Timeline | `setup` or `mobilize` templates |
| `Stakeholders.xlsx` | `stakeholder-analysis` or shared structured-data support |
| `Current_State.xlsx` | shared intake/analysis support |
| `Future_State.xlsx` | shared intake/analysis support |
| `RAID_Plus.xlsx` | `risk-management` or shared intake/review support |
| `Backlog Tracker.xlsx` | `product-planning` / `manage-backlog` |
| `MVP Scope.md` | `product-planning/templates/mvp-definition.md` |
| System Landscape starter | `architecture` template |
| Focus Areas / Solution Directions | `architecture`, `capability-mapping`, or `product-planning`, based on content |
| `99 - System` defaults | owning support skills; copied into the Engagement by `setup` only when still required |

### Path abstraction

Do not mechanically replace `knowledge-hub/` with a new hardcoded relative folder.

Implement one shared path helper that:

1. finds the Engagement root marker;
2. resolves logical destinations;
3. supports spaces in folder names;
4. fails clearly when the user is not working inside a configured Engagement;
5. allows unit tests to point at a temporary Engagement fixture.

Suggested logical names:

```text
sales-handoff
engagement-setup
discovery-research
current-state
future-state
product-roadmap
delivery-readiness
governance-change
final-deliverables
structured-data
ai-system
```

Skills should call the helper or follow a single documented resolution contract. They should not each recreate path logic.

### Existing playbooks

Move authoritative phase behavior into:

```text
skills/mobilize/references/
skills/discovery/references/
```

Afterward:

- keep root playbooks only as human-facing summaries, or remove them after the README/WORKFLOW replacements are complete;
- ensure they are not a competing source of runtime truth.

### Existing root templates

Move templates under their owning skills.

Examples:

- `scope-baseline.md` → `sales-handoff` or `mobilize`;
- `session-note.md` → `discovery-session`;
- `epic-feature.md` → `product-planning`;
- `functional-design.md` → `architecture` or an optional later design skill;
- `salesforce-solution-design.md` → `architecture` or a Salesforce capability pack.

---

## Implementation phases

### Phase 0 — Safety and baseline

- [ ] Read `AGENTS.md`.
- [ ] Ask about branch creation.
- [ ] Record `git status`.
- [ ] Identify user-owned modified and untracked files.
- [ ] Confirm the target build scope with the user.
- [ ] Add or update tests before destructive migration steps.

### Phase 1 — Establish the single-source skill architecture

- [ ] Move `.agents/skills/` to root `skills/`.
- [ ] Add `.agents/skills -> ../skills` compatibility symlink.
- [ ] Add `.claude/skills -> ../skills`.
- [ ] Add `.codex/skills -> ../skills`.
- [ ] Add `.cursor/skills -> ../skills`.
- [ ] Add `.github/skills -> ../skills`.
- [ ] Verify Git records each as mode `120000`.
- [ ] Update `AGENTS.md` with the single-source rule.
- [ ] Update README installation guidance.
- [ ] Do not add hooks in this phase.

### Phase 2 — Build `setup` and Engagement-root resolution

- [ ] Implement `setup`.
- [ ] Implement the folder blueprint.
- [ ] Implement connected and guided SharePoint flows.
- [ ] Implement macOS and Windows OneDrive guidance.
- [ ] Create and validate `engagement.yaml`.
- [ ] Implement the shared Engagement-root/path resolver.
- [ ] Add idempotency and resume tests.

### Phase 3 — Port and adapt `analyze-org`

- [ ] Copy the complete skill from the reference library.
- [ ] Update paths from the reference library's layout to root `skills/`.
- [ ] Add Engagement-aware output routing.
- [ ] Preserve ordinary Salesforce-project fallback behavior.
- [ ] Run the existing dependency-graph tests.
- [ ] Verify refresh preserves vocabulary and manual notes.

### Phase 4 — Build coordination and evidence-collection skills

- [ ] Build `sales-handoff`.
- [ ] Build `mobilize`.
- [ ] Build `stakeholder-analysis`.
- [ ] Build `discovery-session`.
- [ ] Build `discovery-survey`.
- [ ] Build `discovery`.
- [ ] Add compatibility routing from `prep-workshop` and `process-session`.

### Phase 5 — Build Mobilize specialist coverage

- [ ] Build current-state `architecture`.
- [ ] Build current-state `capability-mapping`.
- [ ] Build baseline `business-case`.
- [ ] Build high-level `product-planning`.
- [ ] Build AI assessment mode.
- [ ] Validate every Mobilize deliverable is owned, deferred, or explicitly not applicable.

### Phase 6 — Build Discovery specialist coverage

- [ ] Add future-state `architecture`.
- [ ] Add target-state `capability-mapping`.
- [ ] Add business-case refinement.
- [ ] Add backlog/MVP/roadmap modes.
- [ ] Build `persona-journey`.
- [ ] Build `risk-management`.
- [ ] Build `governance-operating-model`.
- [ ] Build `change-strategy`.
- [ ] Build `delivery-planning`.
- [ ] Build `devops-security`.
- [ ] Build `test-strategy`.
- [ ] Build AI strategy mode.
- [ ] Build `data-migration-strategy`.
- [ ] Mark operational process design as deferred.

### Phase 7 — Migrate reusable assets and active paths

- [ ] Rehome root templates.
- [ ] Rehome blank workbooks and shared defaults.
- [ ] Update support skills to resolve the Engagement root.
- [ ] Update scripts and tests.
- [ ] Update deliverable annotations.
- [ ] Update README, START-HERE, WORKFLOW, and AGENTS.
- [ ] Remove active dependence on the root `knowledge-hub/`.

### Phase 8 — Remove the template `knowledge-hub/`

- [ ] Verify every tracked asset has an owner.
- [ ] Verify tests pass using temporary Engagement fixtures.
- [ ] Verify active docs contain no instructions to use a root `knowledge-hub/`.
- [ ] Remove the directory in a dedicated commit.
- [ ] Verify setup recreates the intended project folders in a temporary workspace.

### Phase 9 — Installation and cross-host QA

- [ ] Validate symlink discovery under Claude Code.
- [ ] Validate symlink discovery under Codex.
- [ ] Validate symlink discovery under Cursor.
- [ ] Validate symlink discovery under GitHub Copilot.
- [ ] Validate global install instructions.
- [ ] Validate project-local install instructions.
- [ ] Validate Windows fallback documentation.
- [ ] Validate relative links from every `SKILL.md`.

---

## Testing requirements

### Skill structure validation

Add a lightweight validator that checks:

- every directory under `skills/` has a `SKILL.md`;
- frontmatter contains only the required fields plus explicitly approved additions;
- `name` matches the directory;
- `description` is non-empty and trigger-focused;
- referenced local files exist;
- templates do not contain unresolved links to removed paths;
- orchestrators only invoke existing skill names.

### Symlink validation

Verify:

```text
.claude/skills -> ../skills
.codex/skills -> ../skills
.cursor/skills -> ../skills
.github/skills -> ../skills
.agents/skills -> ../skills
```

Also verify the hosts see the same skill directory names.

### Setup tests

Use temporary directories, not a real SharePoint workspace.

Cover:

1. Account folder already exists.
2. Account folder does not exist.
3. Engagement folder already exists.
4. Partial Engagement folder tree.
5. Full Engagement folder tree.
6. Resume after interruption.
7. User declines folder creation.
8. Local path is not writable.
9. Marker exists with matching engagement.
10. Marker conflicts with selected engagement.

### Path-resolution tests

Cover:

- invocation from Engagement root;
- invocation from a nested folder;
- path names containing spaces;
- missing marker;
- malformed marker;
- two nested markers;
- temporary fixture override.

### Orchestrator tests

For `mobilize` and `discovery`:

- every slide-defined activity appears in the correct reference;
- every slide-defined deliverable maps to a skill, is deferred, or is explicitly not applicable;
- no coordinator marks a deliverable validated without user confirmation;
- exit behavior asks the user rather than applying invented thresholds;
- the skill-library activity is not treated as a project task.

### `analyze-org` tests

- existing dependency-graph unit tests pass;
- existing project-root mode still works;
- Engagement-aware mode writes under Current State;
- current architecture skill can find and consume the generated index;
- refresh preserves user-authored vocabulary and notes.

### Regression tests

- existing intake/review behavior still works against a temporary Engagement root;
- backlog operations still work through `product-planning`;
- file-format skills still resolve scripts and references after the move to root `skills/`;
- specialty skills remain discoverable;
- no active code assumes a checked-in `knowledge-hub/`.

---

## Acceptance criteria

The implementation is complete when:

1. Root `skills/` is the sole authoritative skill directory.
2. All four host symlinks resolve to the same `skills/`.
3. The temporary `.agents/skills` compatibility symlink works.
4. README explains global and project-local installation.
5. `setup` can guide a user from engagement intake through SharePoint Account/Engagement creation and local synchronization.
6. Setup creates the agreed Engagement folder tree without a `knowledge-hub` wrapper.
7. Later skills can locate the Engagement root through `engagement.yaml`.
8. All 21 primary skills exist with correct frontmatter.
9. Reference files and templates are limited to the agreed requirements.
10. `mobilize` and `discovery` coordinate rather than duplicate specialist work.
11. `analyze-org` is preserved and integrated as Salesforce architecture analysis.
12. Operational process design is explicitly deferred.
13. Existing reusable engines are composed rather than unnecessarily rewritten.
14. The checked-in root `knowledge-hub/` has been removed only after its reusable assets are safely rehomed.
15. Active skills, scripts, and docs no longer require a root `knowledge-hub/`.
16. Automated structure, path, setup, orchestration, and regression checks pass.
17. Existing user changes are preserved.

---

## Explicit non-goals

- Do not implement operational process design.
- Do not invent phase exit criteria.
- Do not automatically distribute surveys.
- Do not build SharePoint credentials or authentication storage.
- Do not add agent hooks without separate approval.
- Do not redesign Salesforce metadata analysis already handled by `analyze-org`.
- Do not duplicate backlog, file-format, intake, or analysis engines without demonstrating a real gap.
- Do not create a new live project workspace inside the skills repository.

---

## Required implementation handoff

When the implementing agent finishes, it should report:

- branch used;
- commits or logical change groups;
- final skill inventory;
- symlink targets and verification results;
- setup workflow demonstration;
- assets moved out of the old `knowledge-hub/`;
- compatibility shims retained;
- deferred work;
- tests run and results;
- any decisions that still require the user's approval.


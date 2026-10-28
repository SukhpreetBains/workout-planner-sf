---
name: create-deliverables
description: Create source-backed, reviewable draft deliverables using a deliverable-type workflow or helps creates new workflows when the asked for deliverable-type does not exist.
---

# Create deliverables

Identify the requested deliverable type and read its workflow before preparing
content or choosing a layout. If the type is unclear, infer it from the user's
request and project context, or ask which deliverable they need. Do not force
another type's format, data schema, or design process onto it.

## Available types

| Type | Use when | Workflow |
| --- | --- | --- |
| Weekly status | The user wants a status report for a reporting period. | [Weekly status](types/weekly-status/workflow.md) |
| Project kickoff | The user wants to align sponsors and the delivery team at the start of an engagement. | [Project kickoff](types/project-kickoff/workflow.md) |

Each type owns its editorial contract, visual directions, templates, assets,
preparation, and verification. Follow the selected type's instructions together
with the shared content alignment requirements below.
Use approved project evidence and keep proposed or unresolved updates distinct
from approved facts. Do not invent client facts or put client data in the skill.

For an initialized Ascent workspace, place drafts in
`workspace/draft-deliverables/<deliverable-name>/`. Elsewhere, follow the user's
destination and repository file organization. Keep draft output reviewable and
promote or publish it only when the user asks.

To add a type, follow [the type authoring guide](types/README.md). A new type
must have its own workflow and must not change the weekly status contract unless
the user requests that change.

If the requested type is not listed, offer to create it either from scratch or
by using an existing type as a starting template. Ask which starting point the
user prefers and which parts of an existing type they want to keep. Do not
present an unimplemented type as available for generation.

## Align content before creating any microsite

For every deliverable microsite, including weekly status, project kickoff, and
new types, gather the relevant evidence for every planned section before visual
generation. Follow the type's source refresh and outline steps first. Present a
concise section-by-section proposal with the intended message, supporting facts
and sources, gaps, and unresolved proposals. Use available project information
before asking the user to supply missing context.

Have a 3–5 question content conversation with the user before building. Group
related sections so every section is covered, adapt questions to the type and
audience, and use answers to shape subsequent questions. Reuse answers already
given; template, color, and icon choices do not count as content questions.
Confirm the intended message, section coverage, key facts and commitments, and
remaining gaps. Show the revised section content and resolve material ambiguity
before generation. Do not treat silence as agreement. Weekly status provides
example questions; other types should ask about their own section content.

### Apply and flag underlying content changes

When the user supplies a concrete addition or correction, compare it with the
underlying review inbox entries and current tracker rows. If it changes a fact,
status, owner, date, decision, commitment, or relationship, apply that specific
change through [workspace-review](../workspace-review/SKILL.md), then flag it to
the user. This workflow authorizes applying clear user-supplied corrections
without a separate confirmation. Do not infer factual changes from editorial
preferences, hypothetical suggestions, or ambiguous wording; clarify those first.
Honor any instruction to keep an edit only in the deliverable.

Identify the affected entry by stable ID and review state. Preserve the user's
clarification as evidence with attribution, and use the review workflow's
validation and write mechanisms. Pending edits remain pending unless the user
also authorizes acceptance. Accepted entry edits can update their tracker row;
report that effect explicitly. Do not restore rejected entries or accept other
pending changes merely to apply a correction. If no matching editable entry
exists, prepare an evidence-backed pending proposal through the supported
workspace workflow and flag that it remains pending. Never invent an entry ID
or modify tracker copies or historical evidence directly.

After the update, refresh and reread the underlying record. Tell the user the
entry ID, old and new values, whether a tracker changed or a proposal remains
pending, and how the change affects the deliverable. Keep pending information
distinct from approved facts. If validation or access blocks the update, report
the blocker and leave the clarification attributed rather than claiming the
underlying content changed. These rules apply to later revisions as well as the
initial content conversation.

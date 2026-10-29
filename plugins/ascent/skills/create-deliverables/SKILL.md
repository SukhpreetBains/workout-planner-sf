---
name: create-deliverables
description: Create source-backed, reviewable draft project deliverables from the Ascent workspace, including weekly status reports, project kickoff presentations, and RAID logs (risks, assumptions, issues, decisions, dependencies, and actions, with an Excel export). Use for any request to create, build, or refresh one of these. Also helps create a workflow when the requested deliverable type does not exist.
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
| RAID log | The user wants a register of the project's risks, assumptions, issues, decisions, dependencies, and actions. | [RAID log](types/raid-log/workflow.md) |

Each type owns its editorial contract, visual directions, templates, assets,
preparation, and verification. Follow only the selected type's instructions.
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

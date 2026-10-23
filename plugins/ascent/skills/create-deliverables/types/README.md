# Deliverable type layout

When a user requests a new type, offer two starting points:

1. Build its workflow, content brief, and output format from scratch with the
   user.
2. Use an existing type as a template, then identify which editorial,
   presentation, and implementation choices to keep or replace.

For example, a project kickoff type could borrow a weekly status visual pattern
if the user wants it, while defining its own kickoff content and review rules.
The existing type remains intact. Do not register project kickoff as available
until its workflow and output have been implemented and verified.

Create one folder per deliverable type, using a stable lowercase name with
hyphens. Add it to the table in the parent `SKILL.md`. Keep the parent skill
focused on selection, shared evidence rules, and draft location.

Each type folder should contain:

- `workflow.md`, with intake, evidence, creation, review, and handoff steps.
- A brief or schema describing the type's content and source requirements.
- Templates and assets used only by that type.
- Type-specific preparation and verification scripts when automation helps.

New types may use different output formats, page structures, visual directions,
or worker counts. Reference shared utilities, such as branding, only when the
type needs them. Keep sample content fictional and dependencies local to the
output package when offline use is required.

Before registering a type, check its input validation, output generation,
source fidelity, and intended preview. Update tests for its own contract. Do
not copy weekly status rules into the parent skill or another type by default.

The top-level `scripts/prepare.py` and `scripts/verify_assets.py` remain
compatibility commands for weekly status. New types should use their own
entry points and document them in their workflow.

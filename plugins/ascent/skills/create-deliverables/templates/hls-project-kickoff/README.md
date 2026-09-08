# HLS project kickoff

Approved reusable template for client-facing Salesforce Health and Life Sciences
Cloud implementation kickoffs. The user approved the template and its module
composition on September 8, 2026, including the photo cover with outlined text
and all three illustration accents.

The full narrative includes purpose, agenda, team, phase progression, schedule,
meeting cadence, norms, story workflow, readiness, accountability, operating
roles, risks, and next steps. Authors can select modules during intake. No
client facts, stakeholder sentiment, or universal delivery criteria are
embedded in shared definitions.

Use `content.example.yaml` with `intake.review.example.json` for the complete
fictional review. Use `intake.example.yaml` to start a fresh, resumable intake.
The review intake cites fictional content; it is not evidence for a real client.

From the create-deliverables skill directory:

```sh
node scripts/build.mjs templates/hls-project-kickoff/content.example.yaml --intake templates/hls-project-kickoff/intake.review.example.json --out /tmp/hls-kickoff --bundle
node scripts/build.mjs --preview-template hls-project-kickoff --out /tmp/hls-modules --bundle
node scripts/build.mjs --preview-module delivery-workflow --out /tmp/hls-workflow --bundle
```

## Reuse and contracts

The new delivery-workflow module owns work-item stages and transitions, plus
project-authored readiness criteria. Delivery approach continues to own project
phases and acceptance. Ways of working owns collaboration conventions.
Existing kickoff selections are explicit so new views and questions do not
change its content contract. Isolated previews render every owned view;
template previews render only the selected views.

New section types are `profiles`, `role-details`, `raci`, `operating-model`,
`phase-progression`, `workstream-schedule`, `meeting-cadence`, `workflow`, and
`disclosures`. Their schemas live in `scripts/lib/delivery-schema.mjs`.
`timeline` remains an alias for the original roadmap; it is not a Gantt chart.

Roles have section-local stable IDs. RACI assignments, operating groups, and
workflow participants reference those IDs. Each RACI activity names at least
one responsible and accountable role; any shared accountability must be
explicit in authored data. Workflow transitions reference stage IDs, including
rework transitions. Schedule items use real ISO dates within an explicit
window and reference stable workstream IDs.

Optional portraits use relative local PNG, JPEG, or WebP paths beside the
content source. The build copies them into the portable package. Omit the
photo field when no asset is available. Do not add real headshots to shared
examples.

Expandable views use native details and summary elements. New disclosures
are independent; the existing agenda retains exclusive expansion. Narrow
screens show an ordered activity schedule. Print styles expose supporting
details and replace the wide chart with the activity list. Existing motion
recipes remain unchanged.

## Review gates

Run `node scripts/test/run.mjs` and the repository collection validator.
Review isolated previews for team-and-responsibilities, delivery-approach,
ways-of-working, delivery-workflow, and kickoff-context, then review the full
HLS template and the original kickoff. Check keyboard operation, long text,
small screens, print detail visibility, and reading without JavaScript.

Brand validation retains the existing font redistribution and cover-vector
warnings, plus informational type-size warnings. Visual approval was recorded on September 8, 2026.

## Template preferences

`instructions.md` is loaded when the template is selected. Intake shows all three
local background images and records the explicit user choice. The example uses
the horizon image; a new intake starts with no selection. Healthcare, whiteboard,
and high-five illustrations decorate purpose, working agreements, and next steps.

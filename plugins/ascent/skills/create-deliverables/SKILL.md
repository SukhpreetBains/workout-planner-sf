---
name: create-deliverables
description: Create three sideways Slalom-branded weekly status microsites from one source-backed synthesis using three Luna subagents, then refine the user's selected direction.
---

# Create deliverables

Create three six-page HTML presentations from one weekly status report. All three
keep the sideways navigation, quiet previous and next controls, direct page
navigation, and sources hidden until the user selects Show sources. The directions
are business, expressive, and animated. Start with the [weekly status brief](templates/weekly-status/brief.md).

## Set the visual inputs

Before generating a new report, show the [Slalom secondary color swatches](assets/secondary-colors.svg)
inline and ask which secondary color the user wants. Offer Cyan `#1BE1F2`, Coral
Red `#FF4D5F`, Purple `#C7B9FF`, and Chartreuse `#DEFF4D`. Ask whether to use
approved Slalom icons, with Yes and No choices. Ask together when both choices are
unknown, and reuse choices already made for this report. Continue evidence work
while waiting, but wait for the selections before visual generation or dispatch.
Save the choices as `secondaryColor: {name, hex}` and `useIconography` in `report.json`.

Use Slalom Blue `#0C62FB`, the selected secondary hue at any opacity, and white,
black, or neutral grays. Slalom Dark Blue `#002FAF` is permitted. Do not invent
other hues, alter supplied artwork, or reduce a content container's opacity.
Check contrast against the composited background. Use Slalom Sans for all three.
Read the [Slalom brand guide](../utilities-ui-generation/branding/packs/slalom/docs/README.md),
especially color, typography, imagery, graphic elements, and accessibility.

When iconography is enabled, the preparation helper packages all 102 approved
icons from the [icon index](../utilities-ui-generation/branding/packs/slalom/assets/iconography/README.md).
Choose icons for their meaning. When disabled, do not show decorative icons.
Navigation controls, timelines, and separately selected imagery remain available.

For the animated direction, inspect approved illustrations and photography in the
branding pack. Show the user a short, relevant asset shortlist when imagery will
shape the story. Use approved people illustrations and icons when they fit the
content. Use approved photography only when the project topic gives it a clear
reason to be there. Keep assets unaltered and local to the output package.

## Prepare one editorial synthesis

Read project instructions and confirm the reporting period when unclear. For an
initialized Ascent workspace, use `workspace-summarize`. Start with approved
tracker rows. Read filed source documents directly when a row is incomplete,
ambiguous, contradictory, or needs context for a connection. Do not reproduce
review-inbox wording mechanically. Select the material updates for the reader,
group related evidence, paraphrase, and explain grounded connections in the
narrative. Cite every material claim with the tracker IDs or underlying sources
that support it. Keep a coverage note about material omissions and evidence gaps.
Keep unresolved proposals separate from approved facts.

Create one `report.json` with the fields in the brief. All three workers use this
same synthesis. A connection may blend into fluent prose when the citations make
its basis clear. Never invent completion, owners, dates, or decisions. The agent
may make a reasoned health assessment when the evidence supports it. Mark it
`healthAssessment: "reasoned"`, state the reasoning and source refs, and label it
provisional in the report. After creating the three drafts, explicitly tell the
user in chat that a reasoned rating was used and ask whether they have additional
information that should change it. If the evidence does not support a rating,
use `Not assessed`.

Grounded suggested actions may appear in `suggestedNextSteps`, clearly separate
from recorded commitments. Do not assign an owner or due date that the source
does not provide. Do not automatically apply suggestions to trackers or other
systems. Retain source qualifications and the evidence cutoff. Use local source
snapshots for cited files as described in the brief. Do not put client data into
skill templates. Ascent outputs belong in
`workspace/draft-deliverables/<report-name>/`; elsewhere follow the user's
destination and repository file organization.

Initialize a new output directory, which the helper refuses to overwrite:

```sh
python3 scripts/prepare.py /absolute/output/path --report /absolute/report.json
```

Run the command from this skill directory, or use its absolute script path. The
helper copies three editable starters, the shared report, Slalom Sans, approved
starter imagery, Anime.js, and the complete approved icon library when enabled.
There is no build step.

## Dispatch exactly three Luna subagents

Use the host's subagent tool to launch three independent workers concurrently,
each explicitly selecting the available Luna model (`gpt-6-luna` on Codex). Give
each a fresh context, the identical shared report, this skill, the weekly status
brief, the chosen palette and iconography settings, the brand guide, and one
output folder. Each worker edits only its folder. Shared facts, assets, and
navigation code remain read-only. Do not substitute a different model or claim
a parallel run if Luna or subagents are unavailable; explain the limitation and
ask for a supported alternative.

All workers preserve the same six pages and order: cover, summary,
accomplishments, next steps, milestones, and risks with decisions. All keep
sideways previous and next controls, keyboard navigation, direct page buttons,
focus management, a live page announcement, print-all behavior, and hidden
numbered source links with an upper-right Show sources toggle. Long pages may
scroll. Keep controls faint until hover or keyboard focus, and visible on touch.

| Worker / folder | Design brief |
| --- | --- |
| `business/` | Business-first and typographic. Dense information remains easy to scan. No decorative motion; use restrained blue, the selected accent, and neutral surfaces. |
| `expressive/` | More visual hierarchy and selective approved imagery. Use restrained page and card transitions. Keep reading calm and clear. |
| `animated/` | Use approved Slalom imagery liberally when relevant. Use local Anime.js v4 for entrances, staggered cards, milestone rail and checkpoints, and pointer responses. Keep all content readable if motion or modules are unavailable, and respect reduced motion. Read the [motion reference](../utilities-ui-generation/references/animejs.md). |

Every worker must render report values with `textContent`, preserve citations and
qualifications, use responsive semantic HTML, working relative asset paths,
visible keyboard focus, and accessible controls. Workers may vary layout and
wording only within the shared synthesis, with no new factual claims.

## Verify and compare

Wait for all workers. Run `python3 scripts/verify_assets.py /absolute/output/path`.
It checks packaged icons and local asset references, including icon names used
inside scripts. Also open each version in a browser and check that every rendered
`img` has loaded (`complete` and `naturalWidth > 0`); this catches missing dynamic
icons. Check factual parity against `report.json`, all six pages, source labels,
navigation, small-screen overflow, keyboard access, print, and reduced motion.
Report checks that could not run; do not describe static inspection as visual
validation.

Serve only the output directory on loopback, for example:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory /absolute/output/path
```

Return links to the comparison page and all three options. Record concrete
readability, flow, and motion observations on the comparison page. Ask which
direction the user wants to refine. Apply follow-on design edits only to that
option unless asked otherwise. Keep factual corrections consistent across all
versions. Leave other drafts available for comparison. Publishing or promoting a
draft requires the user's instruction.

# Weekly status workflow

Create three HTML presentations from one weekly status report. All three
keep the sideways navigation, quiet previous and next controls, direct page
navigation, and sources hidden until the user selects Show sources. The directions
are business, expressive, and animated. Start with the [weekly status brief](templates/brief.md) and [default outline](outline.md).

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
Read the [Slalom brand guide](../../../utilities-ui-generation/branding/packs/slalom/docs/README.md),
especially color, typography, imagery, graphic elements, and accessibility.

When iconography is enabled, the preparation helper packages all 102 approved
icons from the [icon index](../../../utilities-ui-generation/branding/packs/slalom/assets/iconography/README.md).
Choose icons for their meaning. When disabled, do not show decorative icons.
Navigation controls, timelines, and separately selected imagery remain available.

For the animated direction, inspect approved illustrations and photography in the
branding pack. Show the user a short, relevant asset shortlist when imagery will
shape the story. Use approved people illustrations and icons when they fit the
content. Use approved photography only when the project topic gives it a clear
reason to be there. Keep assets unaltered and local to the output package.

## Prepare one editorial synthesis

Read project instructions and confirm the reporting period when unclear. For an
initialized Ascent workspace, run `shared/scripts/sync.py --check-setup`, inspect `shared/scripts/sync.py --status` for unprocessed material, then run `shared/scripts/sync.py --trackers-only` for every fresh report. Stop if the tracker refresh fails. Use `shared/scripts/py` and `ASCENT_PROJECT_ROOT` for these commands. Read the current `workspace/.system/tracker-copies/` and `workspace/.system/applied-updates/` after refresh. Start with approved
tracker rows. Read filed source documents directly when a row is incomplete,
ambiguous, contradictory, or needs context for a connection. Do not reproduce
review-inbox wording mechanically. Select the material updates for the reader,
group related evidence, paraphrase, and explain grounded connections in the
narrative. Cite every material claim with the tracker IDs or underlying sources
that support it. Keep a coverage note about material omissions and evidence gaps in the report data for the chat handoff; do not render it in the presentation.
Keep unresolved proposals separate from approved facts.

Create one `report.json` with the fields in the brief. Read `workspace/.system/outlines/weekly-status.md` when present, otherwise read the legacy `weekly-status-outlined.md`, then fall back to this type's `outline.md`. Validate section names, layouts, categories, and editorial boundaries with `python3 types/weekly-status/scripts/outline.py /absolute/outline.md` before generating. Let the user add, remove, or reorder sections, then save their approved choices to `workspace/.system/outlines/weekly-status.md`. To reset, use `--reset-outline` for a draft and only change the saved outline when the user requests a lasting reset. Offer optional sections after a draft, without creating unsupported commitments. All three workers use this
same synthesis. A connection may blend into fluent prose when the citations make
its basis clear. Never invent completion, owners, dates, or decisions. The agent
may make a reasoned health assessment when the evidence supports it. Mark it
`healthAssessment: "reasoned"` and retain the reasoning and source refs in the
report data. Show the health rating and its source links in the presentation,
without a provisional label or reasoning paragraph. After creating the drafts,
explain in chat how the report was derived: the sources used, reporting window,
evidence cutoff, material gaps, and which conclusions are assessments rather
than source-reported facts. For a reasoned health rating, explain its provisional
nature and evidence-based rationale in chat and ask whether additional information
should change it. Do not put this process explanation or coverage note on the pages. If the evidence does not support a rating,
use `Not assessed`.

Do not add a suggested actions section to the report. Retain source
qualifications and the evidence cutoff. Use local source
snapshots for cited files as described in the brief. Do not put client data into
skill templates. Ascent outputs belong in
`workspace/draft-deliverables/<report-name>/`; elsewhere follow the user's
destination and repository file organization.

Initialize a new output directory, which the helper refuses to overwrite. For
an initialized Ascent workspace, set `ASCENT_PROJECT_ROOT` and use the plugin's
managed Python launcher so tracker and accepted-evidence YAML can be read:

```sh
ASCENT_PROJECT_ROOT=/absolute/project/path /absolute/plugin/shared/scripts/py scripts/prepare.py /absolute/output/path --report /absolute/report.json --project-root /absolute/project/path
```

For a sample or non-Ascent report without `--project-root`, use `python3
scripts/prepare.py /absolute/output/path --report /absolute/report.json` (omit
`--report` for the fictional sample). Run from the `create-deliverables` skill
directory, or use its absolute script path. Use a new version folder for each
draft because the helper refuses to overwrite an existing folder. The
helper copies three editable starters, the shared report, Slalom Sans, approved
starter imagery, Anime.js, and the complete approved icon library when enabled.
There is no build step.

## Dispatch exactly three subagents

Use the host's subagent tool to launch three independent workers concurrently.
At dispatch time, inspect the available model options and select the newest
available model in the lowest-cost tier that supports high reasoning or thinking;
enable the highest available reasoning or thinking setting. Do not hardcode a
model name, since availability, pricing, and controls change. If the host does
not expose enough information to identify a qualifying model or configure high
reasoning, explain the limitation and ask for a supported alternative rather
than claiming the requirement was met. Give each worker a fresh context, the
identical shared report, the parent skill, this workflow, the weekly status brief, the chosen palette
and iconography settings, the brand guide, and one output folder. Each worker
edits only its folder. Shared facts, assets, and navigation code remain
read-only.

All workers preserve cover and summary, followed by the ordered sections in the validated project outline. Default sections are accomplishments, next steps, milestones, and combined risks with decisions. Optional sections use the same layouts across all three styles. All keep
sideways previous and next controls, keyboard navigation, direct page buttons,
focus management, a live page announcement, print-all behavior, hidden
numbered source links with an upper-right Show sources toggle, and an adjacent
Color button that switches among the four approved secondary colors. The chosen
color persists across the three versions and page reloads. Long pages may
scroll. Keep controls faint until hover or keyboard focus, and visible on touch.
Milestones appear as a horizontal, source-order timeline that shows only dates.
Selecting a date opens its milestone below, visibly connected to that date.

| Worker / folder | Design brief |
| --- | --- |
| `business/` | Business-first and typographic. Dense information remains easy to scan. No decorative motion; use restrained blue, the selected accent, and neutral surfaces. Milestones use the rail and caret timeline. |
| `expressive/` | More visual hierarchy and selective approved imagery. Use restrained page and card transitions. Keep reading calm and clear. Milestones use the stem and drawer timeline. |
| `animated/` | Use approved Slalom imagery liberally when relevant. Use local Anime.js v4 for entrances, staggered cards, the spotlight beam milestone timeline, and pointer responses. Keep all content readable if motion or modules are unavailable, and respect reduced motion. Read the [motion reference](../../../utilities-ui-generation/references/animejs.md). |

Every worker must render report values with `textContent`, preserve citations and
qualifications, use responsive semantic HTML, working relative asset paths,
visible keyboard focus, and accessible controls. Workers may vary layout and
wording only within the shared synthesis, with no new factual claims.

## Verify and compare

Wait for all workers. Run `python3 scripts/verify_assets.py /absolute/output/path`.
It checks packaged icons and local asset references, including icon names used
inside scripts. Also open each version in a browser and check that every rendered
`img` has loaded (`complete` and `naturalWidth > 0`); this catches missing dynamic
icons. Check factual parity against `report.json`, all pages, source labels,
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

# Weekly status workflow

Create one HTML presentation from the user's chosen starting template: business,
expressive, or animated. Preserve sideways navigation, quiet previous and next
controls, direct page navigation, and sources hidden until Show sources is selected.
Start with the [weekly status brief](templates/brief.md) and [default outline](outline.md).

## Show templates and choose a starting point

Before generating project content, show the three existing templates using the
bundled fictional sample. Reuse a sample preview when available, or run
`python3 scripts/prepare.py /absolute/preview/path` without `--report` or
`--project-root`. This packages the existing templates for inspection, without
authoring three project reports. Serve that directory on loopback and open its
index in the host's built-in browser when available. Clearly label it as a
fictional template preview. Offer Business (typographic, no decorative motion),
Expressive (selective imagery and restrained transitions), and Animated (imagery
and motion). Ask the user which template to use as a starting point and wait for
their choice. Reuse a choice already provided for this report. Do not generate
multiple project versions by default or dispatch three design workers. If the
user explicitly requests multiple populated versions, prepare only the requested
templates from the same agreed content, in separate output directories.

## Set the visual inputs

Before generating a new report, show the [Slalom secondary color swatches](assets/secondary-colors.svg)
inline and ask which secondary color the user wants. Offer Cyan `#1BE1F2`, Coral
Red `#FF4D5F`, Purple `#C7B9FF`, and Chartreuse `#DEFF4D`. Ask whether to use
approved Slalom icons, with Yes and No choices. Ask together when both choices are
unknown, and reuse choices already made for this report. Continue evidence work
while waiting, but wait for the selections before project visual generation.
Save the choices as `secondaryColor: {name, hex}` and `useIconography` in `report.json`.

Use Slalom Blue `#0C62FB`, the selected secondary hue at any opacity, and white,
black, or neutral grays. Slalom Dark Blue `#002FAF` is permitted. Do not invent
other hues, alter supplied artwork, or reduce a content container's opacity.
Check contrast against the composited background. Use Slalom Sans for the selected template.
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

Create one `report.json` with the fields in the brief. Read `workspace/.system/outlines/weekly-status.md` when present, otherwise read the legacy `weekly-status-outlined.md`, then fall back to this type's `outline.md`. Validate section names, layouts, categories, and editorial boundaries with `python3 types/weekly-status/scripts/outline.py /absolute/outline.md` before generating. Let the user add, remove, or reorder sections, then save their approved choices to `workspace/.system/outlines/weekly-status.md`. To reset, use `--reset-outline` for a draft and only change the saved outline when the user requests a lasting reset. Offer optional sections after a draft, without creating unsupported commitments. Use this synthesis for the selected template. A connection may blend into fluent prose when the citations make
its basis clear. Never invent completion, owners, dates, or decisions. The agent
may make a reasoned health assessment when the evidence supports it. Mark it
`healthAssessment: "reasoned"` and retain the reasoning and source refs in the
report data. Show the health rating and its source links in the presentation,
without a provisional label or reasoning paragraph. After creating the draft,
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

## Align section content before creating the microsite

After gathering evidence and reading the active outline, prepare a concise
section-by-section content proposal in chat. Cover the title/reporting period,
summary and health, and every included outline section. For each, identify the
intended message, supporting sources, relevant facts, gaps, and unresolved
proposals. Gather all relevant available information before asking the user to
fill gaps; do not ask them to repeat facts already available in the workspace.

Have a 3–5 question conversation before creating the project microsite. Tailor
questions to the evidence and outline, grouping related sections so every
section is covered. Ask in short rounds, use the answers to shape the next
question, and reuse answers already given. Template, color, and icon choices do
not count as content questions. For the default outline, useful prompts are:

1. Does the proposed summary and health capture the message for this audience
   and reporting period, or should the emphasis change?
2. Which sourced accomplishments should lead, and is any material progress missing?
3. Are the proposed next steps and milestones correct, including owners, dates,
   and the distinction between plans and completed work?
4. Do the risks and decisions reflect the issues the audience needs to understand,
   and are any additions or exclusions needed?
5. If needed, which optional sections or remaining gaps should be included or
   resolved before drafting?

Adapt these prompts for custom sections rather than ignoring them. Show the
revised section content and resolve material ambiguities with the user before
visual generation. Do not treat silence as agreement. Record additions with
attribution to the user's clarification and preserve uncertainty.

Apply the parent skill's shared underlying-content update rules during this
conversation and subsequent revisions: apply clear user-supplied corrections
through workspace-review and flag the exact changes to the user.

## Prepare the selected template

Initialize a new output directory, which the helper refuses to overwrite. For
an initialized Ascent workspace, set `ASCENT_PROJECT_ROOT` and use the plugin's
managed Python launcher so tracker and accepted-evidence YAML can be read:

```sh
ASCENT_PROJECT_ROOT=/absolute/project/path /absolute/plugin/shared/scripts/py scripts/prepare.py /absolute/output/path --report /absolute/report.json --template business --project-root /absolute/project/path
```

For a sample or non-Ascent report without `--project-root`, use `python3
scripts/prepare.py /absolute/output/path --report /absolute/report.json --template business` (omit
`--report` for the fictional sample). Run from the `create-deliverables` skill
directory, or use its absolute script path. Use a new version folder for each
draft because the helper refuses to overwrite an existing folder. The
helper copies only the selected editable starter, the report, Slalom Sans, approved
starter imagery, Anime.js, and the complete approved icon library when enabled.
There is no build step.

Replace `business` in the command with the user's selection (`business`,
`expressive`, or `animated`). A project report requires an explicit template.
The no-report command is only for fictional template previews. When multiple
populated versions are explicitly requested, run the helper once per requested
template with the same agreed `report.json` and a distinct output directory.
Verify each requested version and return each link; keep factual corrections
consistent across those versions.

## Customize the chosen starting point

Author the selected template using the agreed section content, chosen palette,
iconography settings, and brand guide. No parallel design workers are required.

Preserve cover and summary, followed by the ordered sections in the validated project outline. Default sections are accomplishments, next steps, milestones, and combined risks with decisions. Optional sections use the same layouts across all three styles. Keep
sideways previous and next controls, keyboard navigation, direct page buttons,
focus management, a live page announcement, print-all behavior, hidden
numbered source links with an upper-right Show sources toggle, and an adjacent
Color button that switches among the four approved secondary colors. The chosen
color persists across page reloads. Long pages may
scroll. Keep controls faint until hover or keyboard focus, and visible on touch.
Milestones appear as a horizontal, source-order timeline that shows only dates.
Selecting a date opens its milestone below, visibly connected to that date.

| Template / folder | Design brief |
| --- | --- |
| `business/` | Business-first and typographic. Dense information remains easy to scan. No decorative motion; use restrained blue, the selected accent, and neutral surfaces. Milestones use the rail and caret timeline. |
| `expressive/` | More visual hierarchy and selective approved imagery. Use restrained page and card transitions. Keep reading calm and clear. Milestones use the stem and drawer timeline. |
| `animated/` | Use approved Slalom imagery liberally when relevant. Use local Anime.js v4 for entrances, staggered cards, the spotlight beam milestone timeline, and pointer responses. Keep all content readable if motion or modules are unavailable, and respect reduced motion. Read the [motion reference](../../../utilities-ui-generation/references/animejs.md). |

The author must render report values with `textContent`, preserve citations and
qualifications, use responsive semantic HTML, working relative asset paths,
visible keyboard focus, and accessible controls. Vary layout and
wording only within the agreed synthesis, with no new factual claims.

## Verify and deliver

Run `python3 scripts/verify_assets.py /absolute/output/path`.
It checks packaged icons and local asset references, including icon names used
inside scripts. Also open the selected version in a browser and check that every rendered
`img` has loaded (`complete` and `naturalWidth > 0`); this catches missing dynamic
icons. Check factual parity against `report.json`, all pages, source labels,
navigation, small-screen overflow, keyboard access, print, and reduced motion.
Report checks that could not run; do not describe static inspection as visual
validation.

Serve only the output directory on loopback, for example:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory /absolute/output/path
```

Return the selected report link and open it in the host's built-in browser when
available. Explain the sources, cutoff, gaps, and any reasoned assessments in
chat. Ask what the user wants to refine in this starting point. Keep the sample
template gallery separate from the project deliverable. Apply factual corrections
through the parent skill's underlying-content update workflow. Publishing or promoting a draft
requires the user's instruction.

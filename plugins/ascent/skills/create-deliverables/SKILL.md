---
name: create-deliverables
description: Create three Slalom-branded weekly status microsites from the same project evidence using three Luna subagents, then refine the user's selected direction.
---

# Create deliverables

Create three distinct weekly status options: a straightforward scrolling report,
a business presentation with page navigation, and a colorful animated report.
Use the same facts in all three. Start with [the weekly status brief](templates/weekly-status/brief.md).

## Choose the secondary color

Before generating a new report, show the user the [Slalom secondary color swatches](assets/secondary-colors.svg)
inline and ask: "Which secondary color would you like for this report?"
Resolve the image path from this skill's installed directory when embedding it.
Also provide these labeled choices so the selection works without images:

| Color | Hex |
| --- | --- |
| Cyan | `#1BE1F2` |
| Coral Red | `#FF4D5F` |
| Purple | `#C7B9FF` |
| Chartreuse | `#DEFF4D` |

Wait for the selection before visual generation or dispatching the workers.
Continue gathering evidence while waiting. If the user already selected a color
for this report, reuse it without asking again. Do not silently default to Cyan.
Save the selection in `report.json` as `secondaryColor: {name, hex}` and pass it
to all three workers. For refinements, retain the saved selection unless changed
by the user.

Use Slalom Blue (`#0C62FB`) and that one secondary hue. The agent may use any
opacity from 0% to 100% of the selected secondary color, including translucent
surfaces, borders, gradients, and decorative accents. White, black, and neutral
grays remain available for readable text and backgrounds. Do not introduce other
secondary hues or arbitrary hue shifts. This workflow explicitly permits opacity
variants rather than restricting the selection to the guide's listed tint values.
Check text and controls against their actual composited backgrounds for contrast;
never lower an entire content container's opacity to tint its background.
Keep supplied artwork unaltered.

## Ask about iconography

Before dispatching workers, ask: "Would you like to include Slalom iconography?"
Offer two choices: "Yes, use approved Slalom icons" and "No, keep it typographic."
Ask alongside the secondary-color choice when both are unknown. Reuse an explicit
choice already made for this report. Record `useIconography` as a boolean in
`report.json` and pass it to every worker.

When enabled, consult the [approved icon index](../utilities-ui-generation/branding/packs/slalom/assets/iconography/README.md)
and select only relevant supplied icons. Copy selected assets into the output;
keep them unaltered and accessible. When disabled, use text and ordinary interface
controls, with no decorative icons. This preference does not remove charts,
timeline checkpoints, navigation controls, or separately requested brand imagery.

## Prepare one report

Read the project's instructions and relevant supplied evidence. For an initialized
Ascent workspace, use `workspace-summarize` to ground the report in approved
trackers and source documents. Keep unresolved proposals distinct from approved
facts. Confirm the reporting period when it cannot be inferred; state the evidence
cutoff and gaps. Never infer health, completion, owners, dates, or decisions.

Write `report.json` using the fields in the weekly status brief. Retain source
references per item. Do not put client data into skill templates. All agent-created
outputs for an Ascent project belong in `workspace/draft-deliverables/<report-name>/`.
Elsewhere follow the user's destination and repository file organization.

Read the Slalom pack's [brand guide](../utilities-ui-generation/branding/packs/slalom/docs/README.md),
color, typography, and imagery guidance. These are web experiences, including the
page-based option, so use Slalom Sans. Use the supplied Slalom assets unaltered.

Initialize a new output directory (existing directories are refused):

```sh
python3 scripts/prepare.py /absolute/output/path --report /absolute/report.json
```

Run the command from this skill directory, or use its absolute script path.
The helper copies three editable starters, the shared report, and only the needed
brand and Anime.js assets. There is no build step.

## Dispatch exactly three Luna subagents

Use the host's subagent tool to launch three independent workers concurrently,
each explicitly selecting the available Luna model (`gpt-6-luna` on Codex).
Give each a fresh context, the identical `report.js`, this skill, the weekly status
brief, the chosen secondary color and opacity rules, the brand guide, and its own output folder. Each worker reads its starter
and edits only its assigned folder. Shared facts and assets remain read-only. Adapt starter color tokens to the selected palette; starter Cyan values are examples, not a user choice.
Do not substitute another model or claim a parallel run if Luna or subagents are
unavailable; explain the limitation and ask for a supported alternative.

Use these distinct briefs, allowing layout adaptation to the actual content:

| Worker / folder | Design brief |
| --- | --- |
| `scroll/` | Vertical scrolling business report. Prioritize clarity and scanning, with restrained blue and neutral surfaces, explicit health, useful tables, and no decorative motion. |
| `pages/` | Business presentation experience. One topic per page, previous/next buttons, keyboard navigation, page counter and focus management. Let long pages scroll. Print all pages. This is an HTML microsite, not a PowerPoint file. |
| `expressive/` | Colorful paginated presentation with previous/next, keyboard navigation, and a page counter. Keep numbered source links hidden by default with an upper-right Show sources toggle. Use Slalom Blue plus the user-selected secondary color at any opacity, approved Slalom imagery as accents, and Anime.js v4 liberally for entrances, staggered cards, scroll reveals, and pointer interactions. Read the [motion reference](../utilities-ui-generation/references/animejs.md). Respect reduced motion and keep all information available without animation. |

Every worker must preserve source qualifications, unknowns, and the same coverage:
summary, accomplishments, next steps, milestones, risks, and decisions needed.
Use textContent for report values. Each delivers responsive semantic HTML, working
relative asset paths, visible keyboard focus, and a short account of checks and gaps.

## Compare and refine

Wait for all workers. Check factual parity against `report.json`, sources, asset
loading, navigation, small-screen overflow, keyboard access, print, and reduced
motion. Use browser checks only when permitted by the user's environment. Report
checks that could not run; do not describe static inspection as visual validation.

Serve only the output directory on loopback, for example:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory /absolute/output/path
```

Return links to `index.html` and all three options. Briefly compare readability,
presentation flow, and motion, recording observations in the output's comparison
page. Ask which direction the user wants to refine. Apply follow-on edits only to
that option unless asked otherwise, keeping factual corrections consistent across
all options. Leave the other versions available for comparison. Publishing or
promoting a draft requires the user's instruction.

# Project kickoff

Create a source-backed editorial presentation for a mixed sponsor and delivery
team. Follow this workflow, not the weekly status authoring workflow. This type
has one presentation direction with varied slide compositions. It does not use
a module registry, archetypes, or the retired template module contract.

## Intake

Ask the user to choose presentation depth each time they create a kickoff,
unless already specified in the conversation:

- **Short executive introduction** (`executive`): approximately 7 slides.
- **Concise core with optional detail** (`core`): approximately 11 slides,
  with user-selected supporting sections after the closing commitments.
- **Complete delivery kickoff** (`complete`): approximately 13 slides,
  expanded as needed for delivery responsibilities, governance, and logistics.

Show the [secondary color swatches](../weekly-status/assets/secondary-colors.svg)
and ask for Cyan, Coral Red, Purple, or Chartreuse unless already selected.
Confirm the project and kickoff date from context. When the date is unknown,
use `Kickoff date to agree`; never substitute the generation date. Use the
mixed sponsor and delivery audience unless the user requests another audience.

## Evidence and outline

For an initialized workspace, use `shared/scripts/py` and
`ASCENT_PROJECT_ROOT` to run `shared/scripts/sync.py --check-setup`, inspect
`shared/scripts/sync.py --status` for unprocessed material, and run
`shared/scripts/sync.py --trackers-only` for every fresh kickoff. Stop if the
tracker refresh fails. Then read `workspace/.system/tracker-copies/` and
`workspace/.system/applied-updates/`. Read original source documents where the reviewed
record is ambiguous or incomplete. Do not ingest or approve pending proposals
as part of creating a presentation.

Read [outline.md](outline.md). If present, use the project's editable
`workspace/.system/outlines/project-kickoff.md`; otherwise save an editable copy
of the type outline there when working in an initialized workspace. Select the
requested depth, then adjust the order and optional topics with the user when
needed. Depth is an editorial starting point, not a fixed slide count. Keep the
opening first. In the complete version, place delivery detail before the closing
commitments; in the core version, optional appendix material follows the close.

Keep all material project assertions traceable to approved evidence. Mark any
suggested approach, meeting rhythm, owner, target, date, scope boundary, or next
action that is not agreed as `unconfirmed`. These remain visibly labeled
"To agree at kickoff". Do not imply a commitment merely because it appears in
a kickoff deck. Do not invent Mobilize or Discovery exit criteria. Separate
accepted decisions from discussion prompts. Report source gaps in the chat.

## Author and prepare

Create a `report.json` using [the content brief](templates/brief.md). The example
contains fictional Northstar content only; replace it completely for real work.
Use message-led headlines, concise copy, and a varied editorial rhythm: an
opening statement, context spread, outcome statements, scope contrast, paired
roles, phase journey, milestone disclosures, decision flow, cadence, and closing
commitments. Vary the composition across the deck: a poster opening, asymmetrical context
spread, outcome typography, contrasting scope territories, role pairings,
stepped delivery sequence, compact cadence, and a dark closing statement.
Use spacing and color areas to group content. Do not use decorative partial
borders, repeated separator rules, or the same heading-and-columns structure
on every slide. Use layout to clarify meaning. Avoid status dashboards, decorative
metric rings, autoplay, ornamental motion, or left borders.

Prepare with:

```sh
python3 <type>/scripts/prepare.py <output-directory> --report <report.json> --project-root <project-root>
```

Use the project's configured Python runtime if system Python lacks PyYAML.
For a labeled fictional preview, omit `--report` and use
`--depth executive`, `--depth core`, or `--depth complete`. The preparer refuses
to replace existing output and validates content before writing. Authored reports
supply their chosen ordered sections, including optional topics; the generator
does not silently discard them to enforce a preset.

The package uses the weekly status source packager and base control styles.
It includes local fonts, logo, and a relevant approved illustration. Sources
are off initially. The same source dialog exposes reviewed rows, accepted
excerpts, and safe document snapshots. Color selection persists per output
package. Previous/next controls, direct page buttons, keyboard navigation, and
print-all remain available. Long slides scroll and mobile layouts stack.

## Verify and hand off

Run `python3 <type>/scripts/test_prepare.py`. Inspect the generated package in
the browser at desktop and narrow widths. Exercise previous/next, direct pages,
keyboard navigation, color selection and reload persistence, Show sources,
citation dialog close/focus return, milestone disclosure, and print-all.
Check all included slides for overflow, readable contrast, source accuracy,
unconfirmed commitments, and sensible pacing. Print must include every slide
and expanded milestone details. Respect reduced-motion preferences.

Open `presentation/index.html` in the built-in browser and provide its link.
Summarize the selected depth, color, source gaps, and any commitments still to
agree. Keep outputs under `workspace/draft-deliverables/<name>/` for initialized
projects. Do not publish without the user's instruction.

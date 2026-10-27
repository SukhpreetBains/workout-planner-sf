# Kickoff content brief

Required top-level properties:

- `project`: nonempty project name.
- `date`: contextual kickoff date or `Kickoff date to agree`.
- `sample`: boolean, true only for explicitly fictional content.
- `depth`: `executive`, `core`, or `complete`, selected by the user.
- `secondaryColor`: approved `{name, hex}` pair: Cyan/#1BE1F2,
  Coral Red/#FF4D5F, Purple/#C7B9FF, Chartreuse/#DEFF4D.
- `sections`: ordered nonempty array. The first layout is `opening`.

Each section has a unique `id`, a short topic `label`, message-led `title`,
optional `intro`, supported `layout`, and nonempty `items` array. Layouts:
`opening`, `editorial`, `outcomes`, `boundaries`, `roster`, `journey`,
`milestones`, `decision-flow`, `rhythm`, `commitments`.

Each item has `title`, `text`, optional `detail` and `frequency`, `state` (`confirmed` or
`unconfirmed`), and `source` (array of source labels). Confirmed items require
sources. Unconfirmed proposals may use an empty array; their uncertainty is
always visible. Milestone items also require `date`, including `Date to agree`
when unknown. Use 1-3 items per slide where practical. Split long material into
additional sections with unique IDs. Sections are not constrained to preset IDs.

Use tracker IDs or workspace-relative document paths as source labels. The
shared source packager validates tracker IDs and packages safe document
snapshots. Optional `sourceLinks` follows the weekly status safe-link rules.
Do not author `sourceDetails`; these are rebuilt from project evidence.

All content, including headlines and introductions, must be supported by the
slide's item sources or explicitly framed as a proposed ambition or discussion
prompt. Preserve dates and qualifications from the evidence. Do not invent a
baseline, target, named owner, or agreed timeline to fill the design.

Use `frequency` for a cadence label such as Weekly or Fortnightly when the
evidence or an explicitly unconfirmed proposal supplies it. Keep that label
out of the item title to avoid repetition.

# Weekly status

Use one report for all three directions. The starter report is fictional sample
data, not evidence. Replace it before presenting a project report.

`report.json` is an object with these fields:

| Field | Shape / meaning |
| --- | --- |
| `project`, `period` | Strings identifying the project and reporting window, including evidence cutoff |
| `secondaryColor` | `{name, hex}` selected by the user from the four Slalom secondary colors; required before visual generation, retained for refinements |
| `useIconography` | Boolean chosen by the user before generation; use approved Slalom icons only when true |
| `sample` | Boolean; true only for clearly labeled fictional demonstrations |
| `health` | Source-backed status, or `Not assessed` |
| `summary` | Concise summary with source labels and freshness limits where relevant |
| `accomplishments` | Array of `{text, source}`; completed or explicitly qualified reported progress |
| `nextSteps` | Array of `{text, owner, due, source}` |
| `milestones` | Array of `{name, date, status, source}` |
| `risks` | Array of `{text, impact, owner, action, source}` |
| `decisions` | Array of `{text, owner, due, source}`; decisions needed, not fabricated approvals |

Use readable file/section references or verified source URLs in `source`. State
`Not provided` for unknown item values. Empty arrays mean no evidence supplied,
not no risks or no work. Source-reported implementation is not verified completion.
Keep original qualifiers when compressing text. Use the same reporting window and
content across all three options. Never bring in unrelated facts to fill a layout.

Adapt the HTML starters to the report, keeping the three design briefs distinct.
The comparison should help a user choose how to communicate the same information.

The expressive option uses six paginated sections with numbered citations.
Sources are always retained, but hidden by default; the upper-right Show sources
button reveals them. Deduplicate citation numbers across the full report.
Provide optional `summarySources` (array of source labels) and `sourceLinks`
(object mapping exact labels to verified HTTPS URLs or `../sources/<name>.html`).
For local evidence, copy only the cited documents into `sources/` as escaped,
readable HTML snapshots within the output package. Preserve source qualifications
and original paths. Never invent document URLs. A citation with no verified link
still opens its source label and explicitly states that the document link is absent.

The expressive presentation fills most of the viewport without a decorative panel
border or footer. Use overlapping left/right chevrons that are faint until hover
or keyboard focus, with visible controls on touch devices. Keep the sources and
print controls similarly understated. Omit the visible page counter; preserve an
accessible page announcement and direct page navigation.

Present milestones as an animated checkpoint timeline in the expressive option.
Keep dates and status verbatim, including unknowns and unconfirmed completion.
The timeline shows source order, not elapsed time or percent completion. Use
Anime.js for the rail reveal, staggered checkpoint entrances, and details, with
static readable content for reduced motion or unavailable JavaScript modules.

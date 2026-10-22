# Weekly status editorial brief

Create one report for three sideways six-page presentations. The starter report
is fictional sample data, not evidence. Replace it before presenting a project
report. The pages are cover, summary, accomplishments, next steps, milestones,
and risks with decisions. Each design may change visual emphasis but must keep
the same sourced meaning, qualifications, and coverage.

## Shared report

`report.json` is an object with these fields:

| Field | Shape and meaning |
| --- | --- |
| `project`, `period` | Project and reporting window, including the evidence cutoff. |
| `secondaryColor` | `{name, hex}` selected from the four Slalom secondary colors. |
| `useIconography`, `sample` | Booleans. Mark fictional demonstrations as samples. |
| `health` | Reported rating, provisional reasoned rating, or `Not assessed`. |
| `healthAssessment` | `reported`, `reasoned`, or `not_assessed`. |
| `healthBasis`, `healthSource` | Explanation and source refs for a reported or reasoned rating. |
| `summary`, `summarySources` | Concise editorial synthesis and supporting source labels. |
| `coverageNote` | Evidence cutoff, material omissions, contradictions, and gaps. |
| `accomplishments` | Array of `{text, source, icon?}`. Preserve whether progress is an agreement, reported implementation, or verified completion. |
| `nextSteps` | Array of `{text, owner, due, source, icon?}` for recorded commitments. |
| `suggestedNextSteps` | Array of `{text, rationale, source, icon?}` for grounded recommendations only. Do not write them to trackers. |
| `milestones` | Array of `{name, date, status, source, icon?}`. |
| `risks` | Array of `{text, impact, owner, action, source, icon?}`. |
| `decisions` | Array of `{text, owner, due, source, icon?}` for decisions needed, not invented approvals. |
| `sourceLinks` | Optional map from exact source label to verified HTTPS URL or `../sources/<name>.html`. |

`icon` is an optional approved icon filename stem from the bundled Slalom icon
index. Use it only when `useIconography` is true and the icon adds meaning.
Every item retains readable tracker IDs or file/section references. Use `Not
provided` for unknown owner or date values. Empty arrays mean no evidence was
selected for that section, not that no work, risks, or decisions exist.

## Editorial rules

Start with approved trackers. Read original filed sources when a row is
incomplete, unclear, contradictory, or needs more context for synthesis.
Select material updates, group related items, paraphrase, and connect facts
when the connection follows from the cited evidence. Do not copy the review
inbox row text verbatim by default. Blend supported interpretation into fluent
prose with enough citations for a reader to inspect the basis. Retain original
qualifiers. Source-reported implementation is not verified completion.

The agent may use `healthAssessment: "reasoned"` only with a cited basis that
explains the rating. Show the rating as provisional in all three versions. After
generation, tell the user that a reasoned rating was used and ask for additional
information that might change it. Never treat a reasoned rating as an approved
tracker update. If evidence is insufficient, use `Not assessed` and
`healthAssessment: "not_assessed"`.

Keep suggested next steps visually separate from recorded commitments. A
suggestion needs a source-backed rationale, but it has no implied approval,
owner, or due date. Never apply it to trackers or other systems automatically.
Never invent dates, decisions, or completion. State evidence gaps in
`coverageNote`. The three designs must use the same report data.

## Sources and interface

All three versions hide numbered citations by default. The upper-right Show
sources control reveals them. Deduplicate citation numbers across the report.
For cited local documents or tracker rows, create escaped readable HTML
snapshots inside `sources/` when possible, preserving source labels and original
paths or row IDs. Copy only cited material. Never invent a document URL. A
citation without a verified link must still reveal its exact label and explain
that the document link is unavailable.

All three use the same sideways navigation contract: previous and next
controls, keyboard left and right arrows, direct page buttons, page focus
management, an accessible page announcement, and print-all behavior. Keep
controls quiet until hover or focus and visible on touch. Let long pages
scroll. The most animated version uses a source-order milestone timeline,
not an elapsed-time or percent-complete chart. Dates and status remain verbatim.
Reduce motion on request and keep static content readable if JavaScript motion
cannot load.

Before delivery, verify every local asset path and every rendered image. A
rendered image passes only when `complete` is true and `naturalWidth` is greater
than zero. Inspect all six pages, including hidden pages, after scripts run.

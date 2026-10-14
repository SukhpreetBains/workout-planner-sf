# Weekly status report template guidance

Use this template for a recurring client-facing weekly (or other cadence)
engagement health readout. Unlike a project kickoff, a status report is a new
artifact each reporting period, not a single living site that gets revised.

## Never fabricate content in a real build

This is the base skill's non-negotiable ("never invent a finding, number,
owner, date, decision, or answer to fill a gap"), restated here because this
template carries more risk than most: it produces a new client-facing
artifact every single reporting period, with no one-time final review gate
the way a kickoff site gets. The same discipline has to hold every week, not
once.

In a real build (never in the template's own static example, which is
explicitly fictional and stays that way):

- Every RAG status, number, date, name, or quote must trace to a current
  tracker row or an explicit user answer — never a plausible-sounding guess,
  even one that would pass a casual glance.
- A field with nothing to support it renders as a gap, not a placeholder
  value. This applies with extra force to `engagement-financials`, which has
  no tracker category backing it (see below) and is therefore gap-heavy by
  default until a consultant answers it directly.
- Do not infer this week's RAG status, activities, or milestones from last
  week's build. Reuse a prior week's *structure*, never its *content*, as a
  starting point.

## Recommended starting composition

Start with every module in the template's order unless the user explicitly
narrows the set — a status report loses its value if a workstream's health
picture is incomplete:

- Title / engagement opener
- Agenda
- Escalation log (items needing client or sponsor support right now)
- Status summary (RAG scorecard, scope status, this week's and next week's
  activity, critical open questions, key milestones)
- Action log
- Timeline / roadmap
- RAID log
- Engagement financials

## Engagement financials is conditional

Confirm with the account executive or resource lead whether financial slides
apply to this engagement before including the `engagement-financials` module
— some engagements review financials in a separate meeting. Offer it, don't
assume it.

Note: the source deck this template is based on includes an "Effort (Planned
vs. Actual)" chart, pasted in manually each week. This system has no
chart/image embedding for authored data, so that view is intentionally not
part of this module. If the user provides supporting material later (a chart
image, an export, a different representation), that can be scoped back in as
a follow-up change to the `engagement-financials` module — do not attempt to
approximate a chart with existing components as a substitute.

## Date format in authored content

Every table cell or list item that shows a date to the client (target dates,
due dates, milestone dates) should read `MM-DD-YYYY`, not `YYYY-MM-DD` — the
ISO form reads as unfamiliar to most readers in a polished client deliverable.
This applies to authored table/list content only, not `meta.date` itself,
which must stay ISO 8601 (`YYYY-MM-DD`) — the system derives the long-form
date shown on the cover from it and enforces the ISO pattern structurally.

## Draft naming: use a date, not a version number

The parent `create-deliverables` guidance names drafts
`<template>-<project>-<version, e.g. v1>`. For this template, use a date
instead, since each week is a new artifact rather than a revision of the
previous one:

```
workspace/draft-deliverables/weekly-status-report-<project-name>-<YYYY-MM-DD>/
```

Use the report's reporting-period date (the Monday of the week being
reported on, or the date the user gives you), not the build date, unless the
user says otherwise.

## RAG status definitions — share with the operator, never render to the client

When this template is selected, show the table below to the user (the
consultant preparing the report) before collecting scorecard answers, so
scoring stays consistent with what their engagement sponsors expect. This is
operator context only. Never include this table, or the "Overall status
combination rule" text, in the rendered client deliverable — the
`status-summary` module's `scorecard` view only ever renders the resolved
Green/Amber/Red status per area, never these definitions.

| Area | Typical source | Green | Amber | Red |
|---|---|---|---|---|
| Overall | Qualitative | No more than one status indicator is Amber; none Red | Two or more indicators are Amber, no more than one Red | More than one Red indicator |
| Scope | Weekly status / prioritization sheet | Scope is understood, agreed, and being properly managed | Scope is not being managed as well as it should be, but leaders are aware and working on it | Scope is changing, not being managed properly, and poses a serious project risk |
| Schedule | Engagement schedule / backlog / SOW | Project is on schedule | Project schedule is at risk | Project is behind schedule |
| Issues / Risks | Risk / issue log | No significant risks | Some risks or issues are impacting the project, or putting schedule, scope, or quality in jeopardy | Significant risks or issues exist that will lead to project failure if not resolved |
| Resources (incl. business) | Weekly status | All roles are currently filled; future roles are being discussed with candidates identified | Open roles causing minor impact, or future roles lack a clear candidate or sourcing strategy | Key open roles are not filled adequately, causing major impact to project progress |

Recommend the consultant review this status definition with the engagement
sponsor and confirm the team shares the same understanding of it, and that
engagement-specific metrics were agreed at kickoff.

## Known deviations from the source deck

- No separate "Open" and "Closed" slides for RAID items or action items —
  both existing modules already render a single table with a status column
  per row, which is used as-is.
- No attendance sub-table on the agenda slide.
- No effort planned-vs-actual chart (see above).

Treat the static example only as fictional layout guidance. Never use it as
project evidence.

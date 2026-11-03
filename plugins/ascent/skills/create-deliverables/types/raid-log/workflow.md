# RAID log workflow

Create one standalone RAID log site: a register with one table per tab
(Risks, Assumptions, Issues, Decisions, Dependencies, Actions), where each row
expands to the fields the table does not show. Follow this workflow, not the
weekly status or kickoff workflows. Read the [content brief](templates/brief.md),
[tabs and fields](tabs.yaml), and [picklists](picklists/README.md) first.

## Intake

Do not ask for an accent color. The starter uses the standard Coral Red, and
readers can switch colors with the page's Color button. Use another approved
color only when the user's request names one. Confirm the project from context.
The evidence cutoff (`asOf`) is the day the trackers are refreshed unless the
user names another date.

The parent skill's content alignment conversation does not apply. A RAID log is
a complete register of tracked items, not an editorial selection, so build it
from the trackers without a section proposal or content questions. Ask only
when the project or cutoff is unclear, and raise gaps and assessments in the
handoff.

## Collect

Every RAID log starts fresh. Do not open, validate, repair, or build on earlier
RAID drafts in `workspace/draft-deliverables/`: they are not evidence, and they
may hold superseded judgments. Never modify an earlier draft folder. Begin from
a new starter written by `collect.py` into a new dated folder, and derive every
value from the current approved trackers and source documents.

Keep the workspace clean. Write any helper scripts or scratch files to a
temporary folder outside the workspace, such as one from `mktemp -d`. The new
draft folder holds only the authored `raid.json` and the prepared site.

For an initialized workspace, use `shared/scripts/py` and
`ASCENT_PROJECT_ROOT` to run `shared/scripts/sync.py --check-setup`, inspect
`shared/scripts/sync.py --status` for unprocessed material, and run
`shared/scripts/sync.py --trackers-only` for every new log. Stop if the tracker
refresh fails. Do not ingest, approve, or reject inbox items as part of
creating a RAID log.

Build the starter log, which refuses to overwrite an existing file:

```sh
ASCENT_PROJECT_ROOT=/absolute/project /absolute/plugin/shared/scripts/py types/raid-log/scripts/collect.py /absolute/draft/raid.json --project-root /absolute/project
```

The starter holds every approved RAID item: the rows in the trackers. A RAID
log is a deliverable, so it holds approved items only. Review inbox proposals,
whether pending, flagged, or rejected, never appear in it, and the preparer
rejects any item that is not an approved tracker row. Values the trackers
already record are filled with `basis: recorded`: owners and raisers from
links, dates, the category, a risk's calculated severity, outcomes from each row's
Resolution column, next actions and resolution plans from the action items
that address the item, and, on each action, the RAID items it addresses. Pending changes to an approved
row are listed in `pendingChanges` for the handoff; the log shows the approved
values.

## Fill the gaps

Read each item's description and cited source documents, and fill every empty
field the evidence supports. Use the order the
[picklists README](picklists/README.md) gives: a value the source states
(`basis: stated`, with `source`), then, where [tabs.yaml](tabs.yaml) allows it,
an assessed value (`basis: assessed`, with `source` and a `reason` naming the
facts used). Owners, raisers, dates, outcomes, next actions, and resolution
plans are never assessed. Use only canonical picklist values; map source
wording such as "P1" or "Sev 2" with the aliases. The
[picklists README](picklists/README.md) explains exactly how each level is
recorded or assessed.

Work through these fields deliberately; they are rarely in the trackers:

- **Priority**: assess every open item that has no recorded or stated value,
  using the priority definitions. Leave closed items without a priority unless
  one is recorded or stated. The preparer rejects assessed priority on closed
  items.
- **Severity** and **Importance**: assess every item on their tabs that has
  no recorded or stated value, open or closed.
- **Resolution / outcome**: recorded from the tracker's Resolution column.
  For a closed item without one, look for how it closed: the choice a
  decision made, how a risk was mitigated or an issue resolved, or what a
  completed action produced. These are often in the description itself;
  state them with the record's sources.
- **Next action**: only ever an open action item that addresses the RAID
  item, linked in the trackers. The starter fills it; it
  is never stated or assessed, and the page links it to the action's row.
  When a source describes a next step that no tracked action covers, leave
  the field empty and list the step in `coverageNote` as an action to add
  through `workspace-add` and review. Never write to the trackers while
  creating a log.
- **Category / impact area**: recorded only, from the row's approved
  Category; the starter fills it. Never state or assess it: the category is
  chosen at ingestion and approved in the review inbox, and the preparer
  rejects a value that differs from the tracker. Leave an uncategorized item
  empty.

As Collect says, never copy values, assessments, or reasons from earlier
drafts.

Judge every assessed value item by item, from that item's own description
and sources. Do not assign levels in bulk, by keyword rules, or with
a script that applies one default. Each `reason` must cite a fact specific to
that item, such as a date, blocker, dependency, or stated impact, not restate
its title or description. For a level, say which part of the level's
definition the fact meets and, when the call is close, why the adjacent level
does not fit. Each
assessed field on an item needs its own reason; the preparer rejects an item
that reuses one reason for two fields, and an open item past its target date
whose assessed priority is not High. The preparer rejects a reason template reused
across more than three items, even with each item's title or description
added to it.

Leave a field `null` only when nothing supports it; the log shows "Not
recorded". In `coverageNote`, count the open items left without a priority and
say why, the open RAID items with no next action, the action items that
address no RAID item, the items with no category, and the items categorized
Unknown / TBD.

Do not change an item's tab, category, or status: the preparer
checks them against the current trackers. Keep titles and
descriptions faithful to the record; tighten wording only when it stays
accurate. Keep every item. To leave one out, add it to `omitted` with a reason
the user can check, such as a duplicate. Write `coverageNote` for the chat
handoff only: the evidence cutoff, how many RAID proposals in the review inbox
are waiting and so left out, fields left unrecorded, assessed values, pending
changes, and contradictions.

## Prepare

```sh
ASCENT_PROJECT_ROOT=/absolute/project /absolute/plugin/shared/scripts/py types/raid-log/scripts/prepare.py /absolute/output --log /absolute/draft/raid.json --project-root /absolute/project
```

Run from the `create-deliverables` skill directory, or use absolute script
paths. The preparer validates every value against the picklists and field
rules, confirms every RAID item is present or omitted with a reason, computes
open or closed and status colors, packages source details for tracker rows
and safe document snapshots, copies fonts and the logo, and
writes the Excel export behind the page's Export to Excel link. The workbook has
a Summary sheet and one sheet per tab with every item and field. Assessed values read "(assessed)" with
the reasoning as a cell comment. It has no source column, because source labels
are internal; it ignores on-screen filters.
It refuses to replace existing output; use a new dated folder for each log.
For a labeled fictional preview, omit `--log` and `--project-root`.

For an initialized project, use a new folder
`workspace/draft-deliverables/raid-log-<YYYY-MM-DD>/` (add `-2`, `-3`, and so on
when one exists) holding `raid.json` and the prepared `site/`. Never put
`raid.json` in the skill.

## Verify and hand off

Run `python3 types/raid-log/scripts/test_picklists.py` and
`python3 types/raid-log/scripts/test_prepare.py` with a Python that has PyYAML.
Serve only the output folder on loopback and open it in a browser at desktop
and narrow widths. Check that:

- every tab opens, and its count matches `raid.json`;
- the Status and Decision filters and search work;
- rows expand and collapse, and expanded rows do not repeat table columns;
- the Next action and Addresses columns show in the table without expanding
  a row; a next action opens its action's row, and an action's Addresses
  opens the RAID item's row, even with filters set;
- the assessed-value tooltip, Show sources, the source dialog, and focus
  return all work;
- the color choice persists after a reload;
- Export to Excel downloads the workbook, and its sheets match the tabs;
- print includes every tab and every item expanded, with each tab's name
  repeated on its pages;
- every rendered image has loaded, and no script errors appear.

Report any check that could not run.

In chat, give the link and explain how the log was derived: the evidence
cutoff, the item count, how many RAID proposals await review and are not in
the log (approve them in the review inbox to include them), which fields were
stated or assessed and
why, fields left unrecorded, pending changes not shown, omitted items, and
contradictions. Name the open RAID items with no next action and any next
steps found in sources that are not yet tracked actions, and offer to add them
through `workspace-add` and review. When items have no category, or actions
address no RAID item, offer to categorize and link them through
`workspace-add` for approval in the review inbox. Ask
whether any assessed value should
change. Do not publish
or promote the draft without the user's instruction.

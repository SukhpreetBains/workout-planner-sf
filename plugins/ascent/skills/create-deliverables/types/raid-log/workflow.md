# RAID log workflow

Create one standalone RAID log site: a register with one table per tab
(Risks, Assumptions, Issues, Decisions, Dependencies, Actions), where each row
expands to the fields the table does not show. Follow this workflow, not the
weekly status or kickoff workflows. Read the [content brief](templates/brief.md),
[tabs and fields](tabs.yaml), and [picklists](picklists/README.md) first.

## Intake

Show the [secondary color swatches](../weekly-status/assets/secondary-colors.svg)
and ask for Cyan, Coral Red, Purple, or Chartreuse unless already chosen for
this log. Confirm the project from context. The evidence cutoff (`asOf`) is the
day the trackers are refreshed unless the user names another date.

## Collect

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

The starter holds every RAID item: approved tracker rows and pending or flagged
review inbox proposals. Rejected proposals are excluded. Values the trackers
already record are filled with `basis: recorded`, including owners and raisers
from links, impact areas from linked workstreams, systems, and business
processes, a risk's calculated severity, dates, and next actions or resolution
plans from action items that address the item. Pending changes to an approved
row are listed in `pendingChanges`; the log shows the approved values.

## Fill the gaps

Read the cited source documents for each item and fill empty fields in the
order the [picklists README](picklists/README.md) gives: a value the source
states (`basis: stated`, with `source`), then, where the field allows it, an
assessed value (`basis: assessed`, with `source` and a `reason` naming the facts
used). [tabs.yaml](tabs.yaml) lists which bases each field allows. Owners,
raisers, dates, outcomes, next actions, and resolution plans are never
assessed. Leave a field `null` when nothing supports it; the log shows "Not
recorded". Use only canonical picklist values; map source wording such as "P1"
or "Sev 2" with the aliases.

Do not change an item's tab, category, review state, or status: the preparer
checks them against the current trackers and inbox. Keep titles and
descriptions faithful to the record; tighten wording only when it stays
accurate. Keep every item. To leave one out, add it to `omitted` with a reason
the user can check, such as a duplicate. Write `coverageNote` for the chat
handoff only: the evidence cutoff, how many items are pending review, fields
left unrecorded, assessed values, pending changes, and contradictions.

## Prepare

```sh
ASCENT_PROJECT_ROOT=/absolute/project /absolute/plugin/shared/scripts/py types/raid-log/scripts/prepare.py /absolute/output --log /absolute/draft/raid.json --project-root /absolute/project
```

Run from the `create-deliverables` skill directory, or use absolute script
paths. The preparer validates every value against the picklists and field
rules, confirms every RAID item is present or omitted with a reason, computes
open or closed and status colors, packages source details for tracker rows,
inbox proposals, and safe document snapshots, copies fonts and the logo, and
writes the Excel export behind the page's Export to Excel link. The workbook has
a Summary sheet and one sheet per tab with every item and field, including
pending items marked "Pending review". Assessed values read "(assessed)" with
the reasoning as a cell comment. It has no source column, because source labels
are internal; it ignores on-screen filters.
It refuses to replace existing output; use a new dated folder for each log.
For a labeled fictional preview, omit `--log` and `--project-root`.

Place drafts in `workspace/draft-deliverables/raid-log-<YYYY-MM-DD>/` for an
initialized project. Keep the authored `raid.json` beside the output folder,
not in the skill.

## Verify and hand off

Run `python3 types/raid-log/scripts/test_picklists.py` and
`python3 types/raid-log/scripts/test_prepare.py` with a Python that has PyYAML.
Serve only the output folder on loopback and open it in a browser at desktop
and narrow widths. Check that:

- every tab opens, and its count matches `raid.json`;
- the Status, Review, and Decision filters and search work;
- rows expand and collapse, and expanded rows do not repeat table columns;
- the assessed-value tooltip, Show sources, the source dialog, and focus
  return all work;
- the color choice persists after a reload;
- Export to Excel downloads the workbook, and its sheets match the tabs;
- print includes every tab and every item expanded, with each tab's name
  repeated on its pages;
- every rendered image has loaded, and no script errors appear.

Report any check that could not run.

In chat, give the link and explain how the log was derived: the evidence
cutoff, approved and pending counts, which fields were stated or assessed and
why, fields left unrecorded, pending changes not shown, omitted items, and
contradictions. Ask whether any assessed value should change. Do not publish
or promote the draft without the user's instruction.

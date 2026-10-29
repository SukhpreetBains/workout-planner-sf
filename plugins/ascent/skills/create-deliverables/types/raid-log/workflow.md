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
value from the current trackers, inbox, and source documents.

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

The starter holds every RAID item: approved tracker rows and pending or flagged
review inbox proposals. Rejected proposals are excluded. Values the trackers
already record are filled with `basis: recorded`, including owners and raisers
from links, impact areas from linked workstreams, systems, and business
processes, a risk's calculated severity, dates, and next actions or resolution
plans from action items that address the item. Pending changes to an approved
row are listed in `pendingChanges`; the log shows the approved values.

## Fill the gaps

Read each item's description and cited source documents, and fill every empty
field the evidence supports. Use the order the
[picklists README](picklists/README.md) gives: a value the source states
(`basis: stated`, with `source`), then, where [tabs.yaml](tabs.yaml) allows it,
an assessed value (`basis: assessed`, with `source` and a `reason` naming the
facts used). Owners, raisers, dates, outcomes, next actions, and resolution
plans are never assessed. Use only canonical picklist values; map source
wording such as "P1" or "Sev 2" with the aliases.

Work through these fields deliberately; they are rarely in the trackers:

- **Priority**: assess every open item that has no recorded or stated value,
  using the priority definitions. Leave closed items without a priority unless
  one is recorded or stated. The preparer rejects assessed priority on closed
  items.
- **Severity** and **Importance**: assess every item on their tabs that has
  no recorded or stated value, open or closed.
- **Resolution / outcome**: for every closed item, look for how it closed:
  the answer to an answered question, the choice a decision made, how a risk
  was mitigated or an issue resolved, or what a completed action produced.
  These are often in the description itself; cite the record's sources.
- **Category / impact area**: use only names from the starter's
  `impactAreas`: tracked workstreams, systems, and business processes, plus
  the project's saved list in `workspace/.system/raid-impact-areas.yaml`.
  Separate two areas with `; `. When the project has no saved list, draft a
  short one first (about 5 to 10 areas, each `{name, description}` under
  `areas:`), drawn from the project's evidence, and save it. When an item fits
  no saved area, you may add one to the file. Then state or assess each
  item's area from that list. The preparer rejects any other name.

As Collect says, never copy values, assessments, or reasons from earlier
drafts.

Judge every assessed value item by item, from that item's own description
and sources. Do not assign levels or areas in bulk, by keyword rules, or with
a script that applies one default. Each `reason` must cite a fact specific to
that item, such as a date, blocker, dependency, or stated impact, not restate
its title or description. For a level, say which part of the level's
definition the fact meets and, when the call is close, why the adjacent level
does not fit. For an impact area, say why the item belongs to that area. Each
assessed field on an item needs its own reason; the preparer rejects an item
that reuses one reason for two fields, and an open item past its target date
whose assessed priority is not High. The preparer rejects a reason template reused
across more than three items, even with each item's title or description
added to it.

Leave a field `null` only when nothing supports it; the log shows "Not
recorded". In `coverageNote`, count the open items left without a priority and
say why.

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
contradictions. Tell the user about the impact-area list: where it is saved,
whether this run created it or added areas, and that they can edit the file or
ask you to change it, and later logs will reuse it. Ask whether any assessed
value should change. Do not publish
or promote the draft without the user's instruction.

# RAID log content brief

`raid.json` is one object. `collect.py` writes the starter; the agent completes
it; `prepare.py` validates it. `example.json` is fictional sample data only.

## Log

| Field | Shape and meaning |
| --- | --- |
| `project` | Project name shown as the page title. |
| `asOf` | Evidence cutoff, `YYYY-MM-DD`. |
| `sample` | Boolean; true only for fictional content. |
| `secondaryColor` | `{name, hex}`: Cyan/#1BE1F2, Coral Red/#FF4D5F, Purple/#C7B9FF, or Chartreuse/#DEFF4D. |
| `coverageNote` | Gaps, assessments, and contradictions for the chat handoff; never rendered. |
| `omitted` | Array of `{key, reason}` for items deliberately left out. |
| `items` | Every RAID item; see below. |

The preparer adds `vocabulary`, `sourceDetails`, `exportFile`, and each
item's `open`, `tone`, and `citations`. Do not author them.

## Item

| Field | Shape and meaning |
| --- | --- |
| `key` | Tracker ID for an approved row, or the inbox proposal ID for a pending item. |
| `id` | Tracker ID, or `null` while pending review. The page shows "Pending". |
| `review` | `approved` or `pending`. |
| `category`, `tab` | Tracker category and its RAID tab from `tabs.yaml`. Open questions sit on Decisions as "Decision needed". |
| `title`, `description` | The record's Name and Description. |
| `status` | The record's tracker status value, such as `in_progress`. |
| `source` | Source labels for the record itself: its tracker ID, or `proposal:<id>`. |
| `pendingChanges` | Optional inbox proposal IDs that would change an approved row. |
| fields | One key per field `tabs.yaml` gives the tab, such as `owner`, `priority`, or `nextAction`. |

A field is `null` (shown as "Not recorded") or an object:

| Basis | Required keys | Meaning |
| --- | --- | --- |
| `recorded` | `value`, `from` | Taken from tracker data or links; `from` lists the record IDs used. |
| `stated` | `value`, `source` | Stated by cited documents; `source` lists workspace-relative paths. |
| `assessed` | `value`, `source`, `reason` | Agent judgment against the picklist definitions; the page shows the reason in a tooltip. |

Dates use `YYYY-MM-DD`; the page shows mm/dd/yyyy in the table and the long
form in expanded rows. Priority, Severity, and Importance use the canonical
values in their picklist files. Never invent owners, dates, outcomes, or
commitments to fill a field.

# RAID log picklists

Each RAID field with a fixed set of options has one file here. Every RAID log,
on every project, uses only these values; the preparer rejects anything else.
To add a field with options, add a file with the same shape and list the tabs
it appears on.

| File | Field | Tabs |
| --- | --- | --- |
| `status.yaml` | Status, grouped as open or closed | All |
| `priority.yaml` | Priority | All |
| `severity.yaml` | Severity | Risks, Issues |
| `importance.yaml` | Importance | Dependencies |

## Status

Status values come from each category's Status enum in
`shared/schema/trackers.yaml`. `status.yaml` only groups them as open or
closed for the log's filters and gives each one a dot tone: needs attention,
not started or waiting, in progress, done, or no longer active. Show the
tracker value as recorded next to its dot; color is never the only signal.

## Colors

Every status tone and level value names a `color`: red, amber, green, or
grey. The template maps each name to one fixed hex value, so a color means
the same thing on every project and never follows the selectable accent. These
status colors are a deliberate exception to the Slalom palette; the status
word or level always appears beside the color, so color is never the only
signal. `squares: 2` draws a double marker for the top level of a scale.

## Levels

Priority, Severity, and Importance have no tracker column. Fill each one in
this order and stop at the first that applies:

1. **Recorded**: a tracker value the field's `from_tracker` rule maps to a
   level, such as a risk's Calculated Severity. Never override it.
2. **Stated**: the cited source names the level. Map its wording with the
   value's `aliases` and keep the original wording in the evidence.
3. **Assessed**: apply the value definitions to the cited evidence. Mark the
   value assessed and record a basis naming the facts used.
4. Otherwise leave it empty; the log shows "Not recorded".

Never raise a level to make an item look urgent, and never infer an owner or
a date while assessing a level.

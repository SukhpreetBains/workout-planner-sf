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
| `impact-area.yaml` | Category / impact area, read from the tracker schema | All |

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
Impact areas are categories, not levels, so they have no color.

## Levels

Priority, Severity, and Importance have no tracker column of their own. Fill
each one in this order and stop at the first that applies:

1. **Recorded**: a tracker value the field's `from_tracker` rule maps to a
   level. Never override it.
2. **Stated**: the cited source names the level. Map its wording with the
   value's `aliases` and keep the original wording in the evidence.
3. **Assessed**: apply the value definitions to the cited evidence. Mark the
   value assessed and record a basis naming the facts used.
4. Otherwise leave it empty; the log shows "Not recorded".

Never raise a level to make an item look urgent, and never infer an owner or
a date while assessing a level.

### How each level is determined

**Severity** (Risks and Issues) is the level of impact: for a risk if it
occurs, for an issue now.

- *Recorded*, for risks only, from the risk's Calculated Severity. The tracker
  computes it in `shared/scripts/trackers.py` (`apply_computed_fields`) when a
  risk has both Probability (0.1 to 0.9) and Impact. Risk Score is
  Probability times the Impact weight in `shared/schema/trackers.yaml`
  (very low 0.05; low 0.1; moderate and medium 0.2; high 0.4; very high and
  critical 0.8). A score of 0.5 or more is Sev 1, 0.2 or more is Sev 2, and
  anything lower is Sev 3. `severity.yaml` maps Sev 1, 2, and 3 to High,
  Medium, and Low. Only a very high or critical impact with a probability of
  at least 0.625 reaches High.
- Issues have no severity inputs in the tracker, so their severity is always
  stated or assessed. So is a risk's whenever Probability or Impact is blank.
- *Assessed* against `severity.yaml`. High: stops or delays a milestone,
  deliverable, or go-live, or materially affects scope, cost, compliance, or
  a core business outcome. Medium: rework or delay the current phase can
  absorb, or an effect on one workstream with no stated milestone impact.
  Low: a minor or contained effect, or a workaround exists.
- Severity is filled for open and closed items.

**Priority** (all tabs) is how urgently management attention or action is
needed now.

- No tracker records priority, so it is always stated or assessed.
- *Assessed* only for open items, against `priority.yaml`. High: needs action,
  a decision, or escalation before the next dated checkpoint in the evidence,
  blocks or directly threatens a milestone, deliverable, or go-live, or is
  still open after its target date. Medium: needs action this phase, with
  float, a workaround, or no near-term date at risk. Low: monitor only.
- An open item past its target date is always High when assessed; the
  preparer rejects anything else.
- A closed item keeps a priority only when one is stated.

**Importance** (Dependencies) is how much the receiving work needs the
dependency. No tracker records it, so it is stated or assessed against
`importance.yaml`, for open and closed items. Critical: a hard prerequisite
with no stated workaround. High: a delay would move a dated milestone or
deliverable. Medium: partial progress or a workaround is possible. Low: the
work can proceed without it. Critical is drawn with a double marker.

The preparer also enforces how assessments are written (see the workflow): a
reason specific to each item, a separate reason for each assessed field, and
no reason template reused across more than three items.

## Category / impact area

The standard Ascent RAID category ontology lives in one place: the
`Category` column in `shared/schema/trackers.yaml`, with each value's display
name in `enum_labels` and its definition in `enum_definitions`.
`impact-area.yaml` only names that column; `picklists.py` reads the values
from the schema.

The category is chosen once, when the item is proposed: `workspace-add` picks
the value whose definition matches the item's central concern, and the user
approves it in the review inbox with the rest of the item. The RAID log only
records it from the tracker row. It is never stated or assessed while
building a log, and the preparer rejects a value that differs from the
tracker. An approved row with no Category shows "Not recorded"; to fill it,
ask `workspace-add` to categorize existing items and approve the updates.

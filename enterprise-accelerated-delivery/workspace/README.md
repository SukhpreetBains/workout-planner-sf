# Workspace

Everything about the engagement lives here — documents, meeting notes, and
the trackers that hold what we've learned.

## The flow

Drop new files into `inbox/`. The agent files them into the right folder,
proposes tracker updates from what they contain, and you approve those
updates in `/review-updates` before anything is written. Every tracker row
cites the document it came from.

## Folders

| Folder | What goes here | Who writes it |
| --- | --- | --- |
| `inbox/` | New, unprocessed documents — the only folder you need to remember | You |
| `project/` | Project overview, timeline, phase context | You + agent |
| `meetings/` | Session notes and transcripts, named `YYYY-MM-DD - Title` | Agent (via `/add-meeting-notes`) |
| `current-state/` | How things work today — summaries, landscape docs | You + agent |
| `future-state/` | Where things are heading — options, scope, focus areas | You + agent |
| `reference/` | Background material: SOWs, proposals, exports, client docs | Agent files these from the inbox |
| `trackers/` | Four Excel workbooks — the structured memory of the project | Only `/review-updates` (after your approval) |
| `.system/` | Machine-managed: proposed/applied updates, search index, plain-text tracker copies, sync state | Agent + scripts |

## Trackers

Four workbooks, ten categories:

- `stakeholders.xlsx` — stakeholders
- `current-state.xlsx` — pain points, systems
- `future-state.xlsx` — objectives, requirements
- `raid.xlsx` — risks, assumptions, constraints, decisions, open questions

They are normal Excel files — open and edit them by hand whenever you
like. Afterwards, ask the agent to run sync so the search index and the
plain-text copies in `.system/tracker-copies/` catch up. The full schema
(columns, allowed values, what belongs in each category) is defined in
[`.agents/skills/_shared/schema/trackers.yaml`](../.agents/skills/_shared/schema/trackers.yaml).

## Rules of thumb

- Don't hand-edit anything under `.system/` except to review files in
  `proposed-updates/` — everything else there is rebuilt automatically.
- Prefix meeting files with the date so they sort chronologically.
- If you're not sure where a file belongs, just put it in `inbox/` — the
  agent will file it.

# Codex notes

Read this when workspace-collect runs in the Codex app.

## Scheduling

- A task can target only a folder Codex lists as a project. If the Project
  folder is not one yet (for example, setup ran from another project's
  chat), ask the user to open it in Codex first, then create the task.
- Create and update the task with the Codex app's scheduled-task tool
  (`automation_update`). Use a standalone cron task, not a check-in attached
  to the current conversation, targeted at this Project and run locally.
- Recurrence uses an RRULE in the user's local time:
  - weekly: `RRULE:FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0`
  - daily: `RRULE:FREQ=DAILY;BYHOUR=9;BYMINUTE=0`
- Keep the default permissions. Collection needs only the connectors and
  writes inside the Project folder.
- Medium reasoning effort is enough for a collection run.
- The task's ID is the `--task-id` for `COLLECT schedule`.
- Delete a task with the same tool, never by removing its folder under
  `~/.codex/automations/`; Codex restores task folders from its own records.
- Tell the user that runs happen only while the Codex app is open and the
  computer is awake. Codex warns about this when the user quits. A run
  missed while Codex was closed happens once, shortly after it reopens; the
  cursors make that late run collect exactly what arrived since the last one.
- Name the task without its frequency (for example "Ascent collection —
  <Project>"). Codex keeps a task's ID when its schedule changes.

## Notifications

Codex requires every scheduled run's reply to end with an inbox item:

```text
::inbox-item{title="<title>" summary="<one short sentence>"}
```

Use one of these titles:

- `<N> new files in your review inbox` when files were written (`1 new file`
  for one).
- `Collection needs attention` when any source failed.
- `No new material` when nothing was new and nothing failed.

## Running a collection

- Handle each source in one code-execution step: call its connector
  operations, build the payload, run `COLLECT write --input -` (or a payload
  file with `--delete-input`) through the shell tool, and return only the
  counts and file names. Connector results then stay out of the
  conversation, which keeps every later step small.
- Codex asks each task to keep a `memory.md`. One short line at the end of
  the run is enough; do not read it back for collection decisions.

## Known behaviors

- A connector that needs reconnecting can pause a scheduled run until the
  user opens it, without a separate alert. The setup preflight exists to
  catch this while the user is present.
- Never fall back to the in-app browser or desktop tools when a connector
  fails. They need sign-in and screen-recording permission, and they reach
  beyond the saved scope.
- Collection state lives in `workspace/.system/collection-state.yaml`, not
  in the task's `memory.md`.

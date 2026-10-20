# Codex notes

Read this when workspace-collect runs in the Codex app.

## Scheduling

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
- Tell the user that runs happen only while the Codex app is open and the
  computer is awake.

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

## Known behaviors

- A connector that needs reconnecting can pause a scheduled run until the
  user opens it, without a separate alert. The setup preflight exists to
  catch this while the user is present.
- Never fall back to the in-app browser or desktop tools when a connector
  fails. They need sign-in and screen-recording permission, and they reach
  beyond the saved scope.
- Codex gives each task a `memory.md`. Do not rely on it; collection state
  lives in `workspace/.system/collection-state.yaml`.

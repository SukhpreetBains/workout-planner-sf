---
name: workspace-collect
description: Check a Project's saved Slack and Microsoft Teams sources for new material, on a weekly or daily schedule or on request, and place it in workspace/inbox/ for review without ingesting it. Use when the user wants to set up, change, or stop scheduled collection, choose which saved channels, threads, or recurring meetings to collect from, collect new material now, or when a scheduled task asks to run collection.
---

# Workspace Collect

Bring new material from the Project's saved sources into
`workspace/inbox/`, then tell the user it is there. This skill never
ingests: `workspace-add` runs only when the user asks for it.

Locate `shared/` at the installed Ascent plugin root. Set
`ASCENT_PROJECT_ROOT` to the Project folder for every engine command, then
run scripts through `shared/scripts/py` or `shared/scripts/py.cmd`.
`COLLECT` below means `PY <plugin root>/shared/scripts/collect_inbox.py`; the
script lives in the plugin's shared folder, not in this skill. `<contracts>`
means this skill's `contracts/` folder.

Before anything else, confirm the workspace is initialized:

```
PY <shared-skill-dir>/scripts/sync.py --check-setup
```

If it reports the workspace as not ready, stop and offer to hand off to
`ascent-initial-setup`. If it prints an `ascent update:` line, pass that
message to the user once, in plain words, and carry on.

## Ground rules

- Read only the sources that `COLLECT plan` returns. They are the saved
  locations in `workspace/.system/source-context.yaml` marked
  `collect: true`.
- Reach each source only through the operations its contract in
  `<contracts>` lists. Never use search, a browser, desktop or screen tools,
  another connector, or any posting or write operation. If a listed
  operation fails or needs a reconnect or approval nobody can give, record
  the failure with `COLLECT fail` and move on to the next source.
- Work one source at a time: read it, write it with `COLLECT write`, then
  start the next. A stalled source must not hold back files from sources
  that already succeeded.
- Never run `workspace-add`, never move, rename, or delete inbox files, and
  never write trackers.
- Keep message and transcript text out of `workspace/.system/` except the
  temporary payload file, which `write` consumes and you delete. Never store
  credentials or meeting passcodes.

When the current host has its own notes in `references/` (Codex:
[codex.md](references/codex.md)), read them before scheduling or ending a
run.

## Choose what to do

| Request | Section |
| --- | --- |
| Choose or change which sources are collected | **Choose sources** |
| Set up, change, or stop the schedule | **Schedule** |
| "Collect now", or a scheduled task asked for a run | **Run a collection** |

## Choose sources

1. Show the saved locations and which are already collected. The record's
   manager is `scripts/manage-source-context.py` in the installed
   `ascent-initial-setup` skill:
   `PY <manage-source-context.py> export --root <Project folder>`.
2. A platform is supported only when `<contracts>` has a file for it.
   Today that is Slack (a channel, or one thread) and Microsoft Teams (a
   recurring meeting's transcripts). Say plainly that other platforms are
   not supported yet.
3. For a new location, follow the `setup` entry of its contract to resolve
   identifiers, and confirm the result with the user.
4. Ask before the first write, then save with `PY <manage-source-context.py>
   upsert-source --root <Project folder>`, adding `--location-type` when it is not a channel and
   `--collect` when it should be collected. `upsert-source` replaces the
   whole location, so pass every existing value of a location you are
   changing. To stop collecting a location, upsert it without `--collect`.

## Schedule

1. Require at least one collected source; otherwise run **Choose sources**
   first.
2. Ask how often: **Weekly (recommended)** or **Daily**. For weekly, ask the
   day; default to Monday. Ask the time; default to 9:00 in the user's
   timezone. Say that every run sends a notification, even when nothing is
   new, which is why weekly suits most projects.
3. Preflight while the user is here: run each collected source's contract
   `preflight`, one source at a time, and run `COLLECT status` once so the
   Python environment is ready. Reconnect anything that fails now; an
   unattended run cannot wait for the user.
4. If `COLLECT status` shows a schedule with a `task_id`, update that task
   rather than creating another.
5. Create or update the task with the host's scheduling tool: a recurring,
   standalone task (a new conversation for each run) scoped to this Project
   folder, with the host's default permissions and this prompt:

   ```text
   Use $workspace-collect to run the scheduled collection for this project.
   ```

6. Record it:

   ```
   COLLECT schedule --frequency <weekly|daily> [--weekday <day>] --time <HH:MM> --timezone <IANA name> --host <host> --task-id <task id>
   ```

   This starts each source's cursor at now, so the first run brings in only
   material that arrives after the schedule was set.
7. Confirm in one or two plain sentences: when it runs, which sources, and
   that new material waits in the review inbox until they choose to ingest.

To change the schedule, update the host task and run `COLLECT schedule`
again. To stop it, delete the host task and run `COLLECT unschedule`.

## Run a collection

1. Plan:

   ```
   COLLECT plan --contracts-dir <contracts>
   ```

   For each ID in `needs_start`: in a conversation with the user, ask from
   when to collect and rerun `plan` with `--since <ISO time>`; in a
   scheduled run, record `COLLECT fail --source-id <id> --reason "No start
   point; set up the schedule again"`. Mention every `skipped` source and
   its reason in the final message.
2. For each planned source, in order:
   1. Load `<contracts>/<system>.yaml`. Use its `read` entry for the
      source's `location_type`, its `operations`, and the source's `cursor`
      (`cursor_epoch` is the same moment in epoch seconds).
   2. Build the payload described in
      [collection-payload.md](references/collection-payload.md) and save it
      as `workspace/.system/.collect-<source id>.json`.
   3. Run `COLLECT write --input workspace/.system/.collect-<source id>.json`,
      then delete the payload file. `write` drops anything at or before the
      cursor, writes each new file to the inbox safely, and advances the
      cursor.
   4. If reading failed, run `COLLECT fail --source-id <id> --reason
      "<short reason>"` instead.
3. Finish with a short message:
   - Files written: "**N new files** from <sources> are in your review
     inbox. Nothing has been ingested." (Singular for one file.) List each file as a link, then say:
     "Reply **ingest** and I'll run workspace-add now, or run it yourself
     whenever you're ready."
   - A source failed: name it, say why in plain words, and say what fixes
     it (for example, reconnect Microsoft Teams).
   - Nothing new and nothing failed: "No new material from <sources>."
   - Add the host's notification, per its reference.
4. If the user replies to ingest, run `workspace-add` in this conversation.
   Any other reply leaves the files where they are.

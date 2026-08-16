# Skills

Five workflows, each named after what the user is doing. Every skill is a
`SKILL.md` the agent loads and follows; anything two or more skills need
lives in `_shared/`.

## The five workflows

| Skill | When to use it | Writes to trackers? |
| --- | --- | --- |
| `setup` | Once, on a fresh clone — environment, trackers, project basics, first intake | No (proposes only) |
| `add-documents` | Whenever new files land in `workspace/inbox/` | No (proposes only) |
| `add-meeting-notes` | After a workshop, interview, or standup — transcript in, session note + proposals out | No (proposes only) |
| `review-updates` | To approve, edit, or reject proposed updates | **Yes — the only write path** |
| `summarize` | For a narrative picture: current state, a topic, a stakeholder, a week | No (read-only) |

The pipeline they form: documents → extracted findings → proposed updates
→ human review → tracker rows → sync (search index + plain-text copies +
staleness status).

## `_shared/`

- `schema/trackers.yaml` — the single source of truth: 10 finding
  categories, their columns, allowed values, and plain-English
  "what belongs / bar to clear" definitions. Change the trackers here,
  not in the scripts.
- `scripts/` — the engine (~1,100 lines total):

| Script | Job |
| --- | --- |
| `py` / `py.cmd` | Run any script with the project venv, creating it on first use |
| `init_trackers.py` | Create missing tracker workbooks/tabs from the schema (never touches rows) |
| `read_document.py` | Convert `.docx` / `.pdf` / `.pptx` / `.xlsx` to Markdown for reading |
| `validate_updates.py` | Check a proposed-updates YAML: required fields, enums, link IDs, source refs |
| `apply_updates.py` | Write approved updates to the trackers, assign IDs, archive the file, re-sync |
| `sync.py` | Rebuild search index + tracker copies + sync state; `--status` reports what's new or unprocessed |
| `search.py` | Full-text search over documents and tracker rows; `--id PAIN-003` for one row |
| `paths.py` / `trackers.py` | Shared path constants and openpyxl helpers (imported, not run) |

Invocation pattern used throughout the skills:

```bash
.agents/skills/_shared/scripts/py .agents/skills/_shared/scripts/<script>.py [args]
```

## Conventions for editing or adding skills

- A skill is a folder with a `SKILL.md` (frontmatter: `name`,
  `description`) plus an optional `references/` for templates it alone
  uses.
- Keep instructions in plain English and name steps after user actions.
- Scripts a single skill needs live in that skill's folder; anything
  shared goes in `_shared/` — don't duplicate.
- The engine has an end-to-end test in `_shared/scripts/test_engine.py`;
  run it after script changes:
  `.agents/skills/_shared/scripts/py -m unittest discover -s .agents/skills/_shared/scripts`

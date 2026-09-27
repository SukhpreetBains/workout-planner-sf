# Repository Instructions

## Plugin architecture

- Treat `plugins/ascent/skills/` as the only authoritative skill source.
- For local Codex plugin development, refresh the installed cache with `python3 scripts/refresh_codex_plugin.py` from the repository root after editing the authoritative source. Do not edit `.codex/plugins/cache/...` as a durable change. This is the developer path; it always refreshes immediately regardless of branch or working-tree state, unlike the end-user daily job below.
- End users can opt into an unattended daily update job during `initial-setup` (see `plugins/ascent/skills/initial-setup/scripts/check-for-plugin-update.py` and `manage-plugin-update-schedule.py`). That job only fast-forwards a clean `main` checkout, so it intentionally does nothing on a developer's in-progress feature branch.
- Keep skill discovery flat at `plugins/ascent/skills/<skill-name>/SKILL.md`.
- Keep the Ascent plugin self-contained under `plugins/ascent/`.
- Do not add skill-discovery symlinks or host-specific copies of the skill library.
- Keep skill instructions host-neutral.
- Use minimal skill frontmatter containing only `name` and `description`.
- Keep the four host manifests and marketplace catalogs aligned on plugin name, version, and skill path.

## Current implementation state

The following skills are implemented: `initial-setup`, `project-setup`,
`investigate-project`, `workspace-add`, `workspace-review`,
`workspace-summarize`, `create-deliverables`, `update-deliverable-structure`, and
`utilities-ui-generation`.

Do not treat `analyze-org`, `compose-deliverable`, `design-skill-evals`,
`download-teams-transcripts`, `interview-me`, or `recursive-improvement`,
including their TODO-marked references or templates, as executable workflows
or approved delivery guidance.

## Change safety

- Preserve user-owned changes and inspect `git status` before editing.
- Ask whether feature work should use a new branch and offer a suitable branch name.
- Do not invent Mobilize or Discovery exit criteria.
- Do not implement operational process design as part of `analyze-org`.

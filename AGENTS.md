# Repository Instructions

## Plugin architecture

- Treat `plugins/ascent/skills/` as the only authoritative skill source.
- Codex reinstalls a local plugin only when the version in `plugins/ascent/.codex-plugin/plugin.json` differs from its installed copy, and it checks when the Codex app launches. Every change under `plugins/ascent/` must ship with a version bump; without one, existing installs never receive the change. Pull requests into `main` enforce this with `scripts/check_plugin_version_bump.py`, which you can also run locally before pushing.
- For local Codex plugin development, run `python3 scripts/refresh_codex_plugin.py` from the repository root after editing the authoritative source, then relaunch the Codex app. On a feature branch or with uncommitted changes, the script bumps the version and reinstalls; commit that version bump with your change. On a clean `main` checkout (an end user's install) it only pulls, so it never leaves an end user with a local version edit that would block later updates. Do not edit `.codex/plugins/cache/...` as a durable change.
- End users can opt into an unattended update job during `initial-setup` (see `plugins/ascent/skills/initial-setup/scripts/check-for-plugin-update.py` and `manage-plugin-update-schedule.py`). It only fast-forwards a clean `main` checkout, so it intentionally does nothing on a developer's in-progress feature branch; users receive a pulled update the next time they relaunch Codex.
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

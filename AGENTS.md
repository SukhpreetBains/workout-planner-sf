# Repository Instructions

## Plugin architecture

- Treat `plugins/ascent/skills/` as the only authoritative skill source.
- Codex reinstalls a plugin only when the version in `plugins/ascent/.codex-plugin/plugin.json` differs from its installed copy, and it checks when the Codex app launches, whether the plugin's source is local or Git. Every change under `plugins/ascent/` must ship with a version bump; without one, existing installs never receive the change. Pull requests into `main` enforce this with `scripts/check_plugin_version_bump.py`, which you can also run locally before pushing.
- Two marketplace catalogs are registered from this repo. `.agents/plugins/marketplace.json` (marketplace name `ascent`) declares the `ascent` plugin's source as `git-subdir`, pointing at this repo on GitHub — what `codex plugin marketplace add Slalom/ascent` discovers, and what real end-user installs use. `.agents/plugins/marketplace.local.json` (marketplace name `ascent-dev`) declares the same plugin as a `local` source instead, for iterating on this checkout; a Git-sourced plugin is cloned fresh each refresh and never reads uncommitted local edits.
- For local Codex plugin development, run `python3 scripts/refresh_codex_plugin.py` from the repository root after editing the authoritative source, then relaunch the Codex app. It operates on `ascent-dev` (`marketplace.local.json`), never on the real `ascent` marketplace. On a feature branch or with uncommitted changes, the script bumps the version, reinstalls `ascent@ascent-dev`, and removes `ascent@ascent` if it is installed (best-effort, so it is not an error when it is not): Codex loads every enabled plugin, and two plugins with identical skill names loaded together is confusing with no benefit, so only one is ever active at a time. Commit that version bump with your change. On a clean `main` checkout — after your change is committed and merged — the same command pulls the latest release and switches back on its own: removes `ascent@ascent-dev`, reinstalls the real `ascent@ascent`, no separate flag needed. It never leaves an end user with a local version edit that would block later updates. Pass `--release` to switch back immediately instead, with edits still pending. Do not edit `.codex/plugins/cache/...` as a durable change.
- End users can opt into an unattended update job during `ascent-initial-setup` (see `plugins/ascent/skills/ascent-initial-setup/scripts/check-for-plugin-update.py` and `manage-plugin-update-schedule.py`), which still applies to a local-source install (for example, a developer's own machine, or an end user who installed before the Git-sourced marketplace existed). It only fast-forwards a clean `main` checkout, so it intentionally does nothing on a developer's in-progress feature branch; users receive a pulled update the next time they relaunch Codex. An install from the Git-sourced `ascent` marketplace does not need this: Codex clones and version-checks that source itself on every launch, with no background job required. See `docs/installation-and-updating.md` for both paths.
- Keep skill discovery flat at `plugins/ascent/skills/<skill-name>/SKILL.md`.
- Keep the Ascent plugin self-contained under `plugins/ascent/`.
- Do not add skill-discovery symlinks or host-specific copies of the skill library.
- Keep skill instructions host-neutral.
- Use minimal skill frontmatter containing only `name` and `description`.
- Keep the four host manifests and marketplace catalogs aligned on plugin name, version, and skill path.

## Current implementation state

The following skills are implemented: `ascent-initial-setup`, `investigate-project`,
`workspace-collect`, `workspace-add`, `workspace-review`,
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

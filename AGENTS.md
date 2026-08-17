# Repository Instructions

## Skill architecture

- Treat `skills/` as the only authoritative skill source.
- Keep skill discovery flat at `skills/<skill-name>/SKILL.md`.
- Keep `.agents/skills`, `.claude/skills`, `.codex/skills`, `.cursor/skills`, and `.github/skills` as relative symlinks to `../skills`.
- Keep skill instructions host-neutral.
- Use minimal skill frontmatter containing only `name` and `description`.

## Current implementation state

The initial setup, project-context, `workspace-*` knowledge, and `slalom-branding` skills are implemented. Do not treat other TODO-marked skills, references, or templates as executable workflows or approved delivery guidance.

## Change safety

- Preserve user-owned changes and inspect `git status` before editing.
- Ask whether feature work should use a new branch and offer a suitable branch name.
- Do not invent Mobilize or Discovery exit criteria.
- Do not implement operational process design as part of `analyze-org`.

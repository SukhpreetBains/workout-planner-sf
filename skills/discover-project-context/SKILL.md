---
name: discover-project-context
description: Establish or refresh a reusable project brief and canonical source manifest before implementation work begins. Use when Codex is starting work in an unfamiliar project, repeatedly searching files for project references, onboarding to an existing effort, handing context to later skills, or when the user asks to identify local folders, Slack channels, Teams chats/channels, SharePoint locations, stakeholders, terminology, constraints, or other authoritative project context. Inspect high-signal metadata, interview only for unresolved details, resolve source locations without bulk-reading their contents, and persist the result under .codex/project-context.
---

# Discover Project Context

Create the small, durable context map that later skills read before exploring a project. Discover locations and meaning; do not retrieve dense histories in this skill.

## Contract

Write these files beneath the selected workspace root:

```text
.codex/project-context/
├── .gitignore
├── manifest.json
└── brief.md
```

Treat `manifest.json` as the machine-readable source of truth and `brief.md` as its compact human-readable projection. Read [references/context-contract.md](references/context-contract.md) before writing either file.

Use `scripts/project_context.py` for initialization, source updates, rendering, and validation. Do not invent a parallel context file when the manifest already exists.

## Workflow

### 1. Select the workspace

- Use the current repository or workspace root when it is unambiguous.
- If several roots plausibly represent different projects, ask which project this context describes.
- Keep one manifest per project. Never combine unrelated projects merely because their files share a parent folder.

### 2. Reuse before discovering

- Check `.codex/project-context/manifest.json` first.
- If it exists, validate it and identify only missing, stale, or task-relevant fields.
- Read `brief.md` before any broader exploration. Refresh instead of restarting.

Run:

```bash
python3 <skill-dir>/scripts/project_context.py init --root <workspace-root>
python3 <skill-dir>/scripts/project_context.py validate --root <workspace-root> --allow-incomplete
```

`init` is non-destructive and does not overwrite an existing manifest.
It also creates a directory-local `.gitignore` so manifests and later cached excerpts stay local by default. Tell the user that the context store is intentionally untracked.

### 3. Perform a bounded metadata pass

Inspect only high-signal anchors needed to infer the project identity and likely source locations:

- `AGENTS.md`, existing `.codex/` instructions, and repository metadata
- top-level `README`, package or build manifests, and project configuration
- names of top-level folders and files under obvious `specs`, `docs`, `requirements`, or `design` directories
- git remote and branch metadata when available

Read the smallest relevant slice. Do not recursively grep document contents for project names, open many candidate files, or fetch message histories. Record inferred facts as provisional until the user or an authoritative source confirms them.

### 4. Interview by gap

Ask only questions whose answers materially improve later retrieval. Prefer one compact batch of at most three questions. Skip anything already clear.

Resolve these fields in order:

1. Project objective and the current deliverable or phase.
2. Canonical requirements, decisions, status, and implementation locations.
3. Remote sources that cannot be inferred safely: Slack, Teams, SharePoint, issue trackers, or other systems.

Ask for names or links the user naturally knows; do not require connector IDs. Offer likely locations discovered in the metadata pass for confirmation. Read [references/interview-guide.md](references/interview-guide.md) for the gap rubric and examples.

### 5. Resolve locations, not histories

For each user-provided remote source:

- Resolve the canonical URL or stable connector identifier.
- Confirm ambiguous matches before recording them.
- Inspect only enough metadata to establish identity, accessibility, purpose, and scope.
- Do not read a full Slack/Teams history or recursively fetch SharePoint documents here.
- Do not search private Slack content without explicit consent.
- Record unavailable or permission-blocked sources in `open_questions`; do not silently substitute a different location.

Use source kinds `local`, `slack`, `teams`, `sharepoint`, `web`, or `other`. Put connector-specific search terms in `query_hints` so retrieval can remain narrow later.

### 6. Persist and validate

Set project fields, then add one source entry for each distinct canonical location:

```bash
python3 <skill-dir>/scripts/project_context.py set-project \
  --root <workspace-root> \
  --name "Project name" \
  --objective "Current objective" \
  --phase "Current phase"

python3 <skill-dir>/scripts/project_context.py upsert-source \
  --root <workspace-root> \
  --id requirements \
  --kind local \
  --label "Requirements" \
  --locator "specs/project/design.md" \
  --purpose "Canonical requirements and acceptance criteria" \
  --authority canonical \
  --priority 5

python3 <skill-dir>/scripts/project_context.py render-brief --root <workspace-root>
python3 <skill-dir>/scripts/project_context.py validate --root <workspace-root>
```

- Use workspace-relative paths for local sources when possible.
- Store no credentials, tokens, copied private messages, or full document content in the manifest.
- Mark confidential source locations with the appropriate `sensitivity` value.
- Keep unresolved but important gaps explicit in `open_questions`.
- Keep `.codex/project-context/` excluded from version control when it contains internal or confidential locations. Do not remove or broaden its directory-local ignore rule without explicit user intent.

## Handoff

Report the manifest path, confirmed source count by kind, any permission gaps, and the next recommended action. Tell later skills to read `brief.md` and `manifest.json` before searching. Invoke `$retrieve-project-context` only when the user needs source content gathered for a concrete task.

Do not claim that remote content was reviewed when this skill only resolved its location.

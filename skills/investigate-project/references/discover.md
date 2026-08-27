# Map Mode — Discover Project Context

Create the small, durable context map that later skills read before exploring a project. Discover locations and meaning; do not retrieve dense histories in this mode — that is evidence mode's job (`retrieve.md`).

## Contract

Read [context-contract.md](context-contract.md) before writing the local projection. Do not make `manifest.json` a second independently maintained source inventory.

Discovery is read-only and lightweight. It returns a shortlist of canonical source references and narrow retrieval hints—not file contents, message bodies, document bodies, transcripts, or connector payloads. Every recorded source carries a bounded access state (`available`, `unavailable`, or `unknown`) and a short reason.

Use the initial-setup `scripts/manage-source-context.py` for shared source updates. Use `scripts/project_context.py` to initialize, import, render, measure, and validate the machine-local projection.

## Workflow

### 1. Select the workspace

- Use the current repository or workspace root when it is unambiguous.
- If several roots plausibly represent different projects, ask which project this context describes.
- Keep one manifest per project. Never combine unrelated projects merely because their files share a parent folder.

### 2. Reuse before discovering

- Check `workspace/.system/source-context.yaml` first and validate it with the initial-setup manager.
- Check `workspace/.system/project-context/manifest.json` next. If it exists, validate it and import the shared record before identifying missing, stale, or task-relevant fields.
- Read `brief.md` before any broader exploration. Refresh instead of restarting.

Run:

```bash
python3 <skill-dir>/scripts/project_context.py init --root <opportunity-root>
python3 <initial-setup-skill-dir>/scripts/manage-source-context.py validate --root <opportunity-root>
python3 <skill-dir>/scripts/project_context.py import-source-context --root <opportunity-root> --allow-incomplete
python3 <skill-dir>/scripts/project_context.py validate --root <opportunity-root> --allow-incomplete
```

`init` is non-destructive and does not overwrite an existing local manifest. It also creates a directory-local `.gitignore` so manifests and later cached excerpts stay local by default. Tell the user that the ranked context cache is intentionally untracked while the project communications record remains project-owned.

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

Ask for names or links the user naturally knows; do not require connector IDs. Offer likely locations discovered in the metadata pass for confirmation. Read [interview-guide.md](interview-guide.md) for the gap rubric and examples.

### 5. Run a measured, per-system source pass

For each system that may contain project context, use the smallest available read operation to identify candidate locations. This is a source-discovery pass, not retrieval:

- **Chat systems (Slack, Teams, or equivalent):** resolve the channel, chat, or team; inspect metadata and at most 10 recent or search-result messages per candidate, with a default cap of 30 preview items across the system.
- **SharePoint:** validate a known hostname/site path, resolve the document library, and list immediate folder items. When the exact site is unknown, use a narrow metadata search first. Inspect at most 10 item names plus metadata per candidate, with a default cap of 30 items across the system. Record the canonical URL plus exposed hostname, site path, drive ID/name, and folder path.
- **Other document systems:** validate the container and inspect at most 10 item names plus metadata per candidate, with a default cap of 30 items across the system.
- **Local workspaces:** inspect at most 30 top-level names, targeted filenames, and repository metadata. Do not bulk-read documents or recursively search text.
- **Other systems:** use the closest equivalent metadata or short-preview operation, cap it at 10 items by default, and state the applied cap.

These are per-system exploration caps, not retrieval budgets. Stop at the cap even if more candidates exist. If a different cap is necessary, state it before the pass and record the actual cap in `discovery_runs.exploration_caps`.

Route by the runtime's exposed capabilities rather than assuming a connector name, API, tenant, or permission model. Never search private content without explicit consent. Stop once a canonical locator, stable ID, direct link, or local path is resolved; leave anything else as an `open_question`.

Record only confirmed source references, access state/reason, and narrow retrieval hints in the project communications record. Keep unconfirmed candidates in the conversational report. Do not copy preview text, message bodies, document bodies, credentials, permission payloads, or opaque connector payloads into either output.

Measure the pass after the scan: count connector calls, candidate locations considered, locations recorded, preview items inspected, and inspected characters. Prefer a runtime-reported token count; otherwise estimate input tokens as inspected characters divided by four (rounded up). Record the totals and the stated per-system caps with:

```bash
python3 <skill-dir>/scripts/project_context.py record-discovery \
  --root <opportunity-root> \
  --sources-considered 6 \
  --sources-recorded 3 \
  --connector-calls 4 \
  --items-inspected 18 \
  --characters-inspected 3200 \
  --cap local=30 \
  --cap chat=30 \
  --cap document=30 \
  --cap other=10
```

The resulting `discovery_runs` entry provides an auditable token estimate without retaining source content. If the supplied preview would exceed the bounds above, stop and switch to evidence mode (`retrieve.md`) for a task-specific, ranked retrieval.

### 6. Resolve locations, not histories

For each user-provided remote source:

- Resolve the canonical URL or stable connector identifier.
- Confirm ambiguous matches before recording them.
- Inspect only enough metadata to establish identity, accessibility, purpose, and scope.
- Do not read a full Slack/Teams history or recursively fetch SharePoint documents here.
- Do not search private Slack content without explicit consent.
- Record unavailable or permission-blocked sources with `access.state: unavailable` and a short `access.reason`; preserve the reference and add a concise `open_questions` gap when useful. Do not try broader access, change permissions, or silently substitute a different location. Use `unknown` when accessibility was not determined.

Use source kinds `local`, `slack`, `teams`, `sharepoint`, `web`, or `other`. Put connector-specific search terms in `query_hints` so retrieval can remain narrow later.

### 7. Persist, import, and validate

After user confirmation, add each distinct canonical location to the shared record, then import it into the local projection. For SharePoint, include every identifier the runtime exposed:

```bash
python3 <initial-setup-skill-dir>/scripts/manage-source-context.py upsert-source \
  --root <opportunity-root> \
  --id engagement-folder \
  --kind sharepoint \
  --name "Engagement folder" \
  --locator "https://contoso.sharepoint.com/sites/Consulting/Shared%20Documents/Acme/Engagement" \
  --identifier hostname=contoso.sharepoint.com \
  --identifier site_path=/sites/Consulting \
  --identifier drive_name="Shared Documents" \
  --identifier folder_path="Acme/Engagement" \
  --purpose "Canonical project workspace" \
  --authority canonical \
  --priority 5 \
  --access-state available \
  --access-reason "Folder identity was confirmed during discovery."

python3 <skill-dir>/scripts/project_context.py set-project \
  --root <opportunity-root> \
  --name "Project name" \
  --objective "Current objective" \
  --phase "Current phase"

python3 <skill-dir>/scripts/project_context.py import-source-context --root <opportunity-root>
python3 <skill-dir>/scripts/project_context.py validate --root <opportunity-root>
```

- Use workspace-relative paths for local sources when possible.
- Preserve the setup-generated `account`, `opportunity`, platform connection states, and unknown compatible fields.
- Store no credentials, tokens, copied private messages, or full document content in the shared record or local projection.
- Mark confidential source locations with the appropriate `sensitivity` value.
- Keep unresolved but important gaps explicit in `open_questions`.
- Keep `workspace/.system/project-context/` excluded from version control when it contains internal or confidential locations. Do not remove or broaden its directory-local ignore rule without explicit user intent.

## Handoff

Report the project communications record status, local manifest path, confirmed source count by kind, discovery measurement (including estimated or reported tokens), permission gaps, and next recommended action. Tell later skills to read the shared record, then `brief.md` and `manifest.json`, before searching. Switch to evidence mode only when the user needs source content gathered for a concrete task.

Do not claim that remote content was reviewed when this skill only resolved its location.

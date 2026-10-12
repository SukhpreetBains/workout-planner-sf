# Opportunity Workspace Walkthrough

This guide explains how identity-only initial setup hands an Opportunity into the governed knowledge lifecycle documented in the plugin [workflow overview](../plugins/ascent/README.md).

## 1. Run `initial-setup`

Start with a shared workspace or choose a local-only location. For SharePoint,
setup can reuse an existing Account folder or guide the user through creating a
missing one. The skill:

1. Verifies Python 3.10 or newer.
2. Selects shared or local-only storage and resolves its local Account path.
3. For SharePoint, guides the user through locating or creating the Account
   folder and connecting it to OneDrive when necessary.
4. Asks whether the user is starting a new Opportunity or joining an existing one.
5. Confirms the Account name, Opportunity name, local path, applicable
   user-reported storage access, and local write readiness.
6. Records only the confirmed Account and Opportunity identity while preserving existing project details.

Before changing anything, setup runs a read-only check showing what exists and
what is missing. A local-only workspace is valid, but it is not shared or
synchronized automatically.

## 2. Prepare the Opportunity folder

Setup copies the canonical workspace template bundled with `initial-setup` into the Opportunity:

```text
<Account>/
  <Opportunity>/
    AGENTS.md
    workspace/
      inbox/
      draft-deliverables/
      project/
      meetings/
      current-state/
      future-state/
      reference/
      trackers/
      .system/
    Deliverables/
      Mobilize/
      Discover/
      Deliver/
      Transition/
```

The operation is resumable. Existing files and tracker rows are preserved, while missing template files and folders are created. All agent-created project work stays inside `workspace/`. A person can promote reviewed material into `Deliverables/`.

After the folder exists, setup follows the [host workspace-access guide](../plugins/ascent/skills/initial-setup/references/host-workspace-access.md) to make the confirmed Opportunity folder available to future conversations. Host-specific controls live in separate references under `initial-setup`.

## 3. Record Opportunity identity

Machine-readable project data goes into `workspace/.system/project.yaml`:

```yaml
account: <account name>
opportunity: <opportunity name>
```

The idempotent identity script reconciles these two identity fields without
replacing the file or changing any other existing keys. It updates the Account
and Opportunity row in `workspace/project/Project Overview.md` while preserving
all other readable content. Setup does not request or create optional project
details.

## 4. Record external project locations

Setup can identify relevant SharePoint, Slack, and Microsoft Teams locations. It asks before saving confirmed locations to:

```text
workspace/.system/source-context.yaml
```

This project communications record contains source locations and access state, not message bodies, document contents, credentials, or copied files.

It is separate from `workspace/.system/sources.yaml`, which inventories individual documents ingested into the workspace.

## 5. Initialize the workspace engine

One orchestrating command initializes:

- a Python environment in the per-user Ascent cache, outside the synced folder
- `workspace/.system/.venv-path`, which points to that cached environment
- four Excel tracker workbooks
- plain-text tracker copies
- the full-text search index
- proposed and applied update queues

Set `ASCENT_OPPORTUNITY_ROOT` to the Opportunity folder. Set `ASCENT_PYTHON` to
the exact supported interpreter that should build or reuse the environment.
`ASCENT_CACHE_DIR` can override the default per-user cache root. The launcher
does not install dependencies silently; installation requires the explicit
`--install-dependencies` option after user approval.

The setup command prints the readiness report defined by the authoritative
[setup readiness contract](../plugins/ascent/skills/initial-setup/references/setup-readiness.md).

The trackers are:

- `stakeholders.xlsx`
- `current-state.xlsx`
- `future-state.xlsx`
- `raid.xlsx`
- `delivery.xlsx`

## 6. Hand documents to a fresh chat

Initial setup does not ask about documents, inspect `workspace/inbox/`, or process source material. Existing documents remain untouched.

After the final setup checklist, place the first source document in the confirmed absolute `<Opportunity folder>/workspace/inbox/` path. If it is already there, leave it in place. Then open a fresh agent chat with the same Opportunity folder open. Start that new chat before ingestion so setup history does not consume the context needed to inspect and reason over source material. Use this starter prompt:

```text
Use workspace-add to process the documents in this Opportunity workspace inbox.
```

`workspace-add` files the document and prepares evidence-backed proposals. If it finds proposals, the review inbox comes afterward for approving them; the trackers change only through `workspace-review`.

## 7. Ingest documents and capture meetings

Place new material in `workspace/inbox/`, then invoke `workspace-add`.

The skill:

1. Reads or converts each document.
2. For a meeting transcript or raw notes, writes a structured session note under `workspace/meetings/` and files the transcript beside it. For everything else, files it into `current-state/`, `future-state/`, or `reference/`.
3. Records it in `workspace/.system/sources.yaml`.
4. Extracts evidence-backed entities (people, roles, organizations, systems, phases, and more) and signals (pain points, requirements, risks, decisions, action items, and more), classified with the category definitions in `shared/schema/trackers.yaml`, and the relationships the sources state between them.
5. Writes proposed changes into `workspace/.system/proposed-updates/`.
6. Validates the proposals and refreshes the search index.

It does not modify the trackers.

## 8. Review proposed updates

Invoke `workspace-review` to inspect pending changes. For each proposal, it shows:

- a loopback-only visual review link when proposals are ready
- category counts and a completed-versus-remaining progress bar
- one governed proposal card at a time, with autosaved edits and source evidence

- the proposed addition or change
- supporting source evidence
- whether it is a new row or an update
- the existing tracker row when applicable

The user can approve, edit, or reject each proposal. Only approved changes are written into the Excel trackers. Applied proposal files move to `workspace/.system/applied-updates/`.

This is the only skill authorized to write tracker changes.

## 9. Investigate or summarize governed evidence

Invoke `investigate-project` to map confirmed project knowledge locations or retrieve bounded, cited evidence for a specific task.

Invoke `workspace-summarize` for current-state summaries, weekly rollups, stakeholder views, system or process deep dives, and future-state summaries.

The summarization skill searches workspace documents and tracker rows, traces important claims to their sources, identifies contradictions and gaps, and can write results beneath `workspace/current-state/` or `workspace/future-state/`. It never changes the trackers.

## 10. Create deliverables

Invoke `create-deliverables` when governed evidence is ready to become a draft client deliverable. Generated artifacts stay in `workspace/draft-deliverables/` until a person reviews and promotes them.

## Ongoing workflow

```text
New documents
    ↓
workspace-add
    ↓
Proposed tracker updates
    ↓
workspace-review
    ↓
Approved tracker knowledge
    ↓
investigate-project or workspace-summarize
    ↓
create-deliverables
```

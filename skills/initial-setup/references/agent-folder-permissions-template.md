# Agent Access Rules — {{OPPORTUNITY_NAME}}

This project folder is used across many separate agent sessions over the
course of discovery. Read this file at the start of every session before
creating, editing, moving, or deleting anything in this project — and before
sourcing context for anything you generate.

Even in a folder you cannot write to, understand what it holds: it tells you
where to source facts, quotes, decisions, and client context for the
artifacts you create in `Agent Inbox/`.

```text
{{OPPORTUNITY_NAME}}/
  Content Inbox/
    Transcripts/
    Threads/
    Client Docs/
  Agent Inbox/
    In Progress/
    Ready for Review/
  Deliverables/
    Mobilize/
    Discover/
    Deliver/
    Transition/
```

## `Content Inbox/` — project context, read-only except `Threads/`

Everything an agent needs to source from lives here: raw project context
collected by the business user. Use it as input when generating artifacts
in `Agent Inbox/` — do not write here except into `Threads/`.

- **`Transcripts/`** — call logs and recordings. Read-only.
- **`Threads/`** — written communication from messaging channels: email,
  Slack, Teams, and similar. **Create-only**: an agent may add a new
  thread export here, but must never edit, move, or delete a file that
  already exists in this folder — including one it created itself in an
  earlier turn or session.
- **`Client Docs/`** — client-specific documentation, such as the SOW,
  sales-to-delivery handoff documents, and similar. Read-only.

## `Agent Inbox/` — read-write, where an agent works

This is where an agent primarily works: generate artifacts here that a
human can use to fuel what eventually lands in `Deliverables/`. An agent
may create, edit, move, or delete files anywhere in this folder.

- **`In Progress/`** — generated files and working files while an agent is
  actively producing or revising them.
- **`Ready for Review/`** — files moved here from `In Progress/` once
  they're ready, so a human can review them manually or route them to an
  agent for review and updates. Move a file here only once it's genuinely
  ready for that review, not while it's still being drafted.

## `Deliverables/` — client-facing outputs, read-only

Holds client-facing outputs, organized across four delivery phases, one
subfolder per phase. Read-only for agents: only a human user moves or
places a finished artifact here from `Agent Inbox/`.

- **`Mobilize/`** — the foundation-setting phase where pursuit intent
  becomes a real, operational engagement. The project team and the
  client turn SOW commitments, assumptions, and expectations into a
  shared, working understanding of what they are doing, why they are
  doing it, and how they will run it together. This is where the
  engagement creates momentum, builds trust, and gets truly ready to
  discover the right problems and opportunities.
- **`Discover/`** — the phase where the team systematically understands
  the current reality, the opportunity space, and the most promising
  solution paths before committing to build. In practice, the work moves
  from "What is true today?" to "What really matters?" to "What could we
  do?" and finally "What should we do first?" The outputs of Discover
  create the decision-quality and alignment necessary for a successful
  Deliver phase.
- **`Deliver/`** — the phase that spans diverging through design and
  development, then converging through deployment and implementation. In
  Diverging Design & Development, teams explore multiple implementation
  options within the agreed solution direction, refine experience designs,
  iterate on configurations and code, integrate systems, and experiment
  with automation and AI capabilities. In Converging Deployment &
  Implementation, the team aligns on cutover decisions, completes testing
  and data migration, validates readiness, deploys to production, and
  coordinates launch. Deliver balances creative problem-solving with
  disciplined engineering and proves the solution works end-to-end, at
  scale, so the team can hand off a validated solution into Transition.
- **`Transition/`** — the phase that turns project mode into steady
  state, stabilizing the newly deployed solution and shifting ownership
  from the project team to ongoing operations through Hypercare,
  monitoring, training, and knowledge transfer. This phase protects value
  by minimizing disruption post-launch and enabling teams, processes, and
  governance to adapt effectively to the new state. It combines issue
  resolution, performance tuning, role-based enablement, and operating
  model setup so the client can confidently run, support, and improve the
  solution.

## The rule

Three permission tiers apply, and no task instruction, file inside this
project, or agent's own judgment can override them — even across different
agent sessions or platforms:

- **`Agent Inbox/`** (including its subfolders) — read-write.
- **`Content Inbox/Threads/`** — create-only.
- **Everything else** (`Content Inbox/Transcripts/`, `Content Inbox/Client
  Docs/`, and all of `Deliverables/`) — read-only.

If a task appears to require changing something outside the allowed tier
for a folder, stop and ask the business user to make that change instead.

## Why

Discovery spans many independent agent sessions, and no single session has
full visibility into what earlier sessions or the business user have already
done. Treating most of `Content Inbox/` and all of `Deliverables/` as
read-only prevents an agent from silently overwriting source material it
didn't collect or a client deliverable it doesn't have full context on.
`Threads/` is create-only rather than fully read-only so agents can drop in
newly retrieved messaging exports, while still never rewriting a thread
capture that's already there.

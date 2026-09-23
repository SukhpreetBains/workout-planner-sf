# Content contract

The microsite is a pure function of one content file. `scripts/lib/content.mjs`
is the enforcing implementation; this document is its description.

Input is `.yaml`, `.yml`, or `.json`. **JSON is a first-class input format** —
the YAML support is a bounded subset (see `../scripts/lib/yaml.mjs`), so when in
doubt, write JSON.

## Shape

Two top-level keys, `meta` and `sections`. Anything else is an error.

## `meta`

| Field | Required | Notes |
|---|---|---|
| `archetype` | yes | Selects `templates/<archetype>/`. Currently `project-kickoff`. |
| `client` | yes | The client's name as they write it. |
| `title` | yes | Sentence case. |
| `subtitle` | no | One line of scope or timeframe. |
| `date` | yes | ISO 8601, `YYYY-MM-DD`. |
| `authors` | no | List of `{name, role}`. `role` optional. |
| `classification` | yes | The confidentiality marker. Appears on the cover **and** in the footer, and the validator checks both. |
| `accent` | yes | One of `cyan`, `coral-red`, `purple`, `chartreuse`. |
| `client_logo` | no | `.svg` or `.png`, path relative to the content file. Forms a partner lockup. |

An unknown key under `meta` is an **error**, not a silent drop — `acccent: cyan`
should fail loudly rather than produce a deliverable with the wrong colour.

### `accent` is enforced structurally

`build.mjs` writes `data-accent="<accent>"` on `<html>`. `tokens.css` defines
`--accent`, `--accent-dark-3` and `--accent-light-3` only inside
`[data-accent="…"]` blocks, and every component references `var(--accent)`
rather than a named secondary. The brand's "at most one secondary colour per
composition" rule therefore cannot be violated by construction. The validator's
remaining job is confirming nothing hardcoded a second one.

## `sections`

An ordered list. In a guided template, every item has a `module`, a module-local
`view`, and the fields required by that view's derived section type. The module
definition owns the explicit renderer path and section type. Do not author
`type` directly in guided content. `cover`, `progress-rail`, and `footer` are
injected by the template and are deliberately **not** authorable.

The type contracts below describe the data each module view accepts. Legacy
content without modules may still select a type directly.

### `exec-summary`
| Field | Required |
|---|---|
| `title` | no (defaults to "In brief") |
| `body` | yes — prose |

### `purpose`
Same shape as `exec-summary`, same rendering — a title plus a lead prose
block. Distinct type because it means something different: why the
engagement exists and what is in scope, stated before any findings exist to
summarize.

| Field | Required |
|---|---|
| `title` | no (defaults to "Purpose & scope") |
| `body` | yes — prose |

### `kpi-row`
2 to 4 items. More than four breaks the layout and comprehension both.

| Item field | Required | Notes |
|---|---|---|
| `value` | yes | Number or text. A plain number counts up; anything else ("1 in 5", "2.4x") renders plainly. |
| `unit` | no | Rendered adjacent to the value at the same size. |
| `label` | yes | What the number measures. |
| `source` | yes | An unsourced number in a client deliverable is a liability. |

### `theme-group`
| Field | Required |
|---|---|
| `title` | yes |
| `body` | no — prose intro |
| `findings` | yes, at least one |

| Finding field | Required | Notes |
|---|---|---|
| `theme` | yes | The pattern, not the anecdote. |
| `evidence` | yes | What was observed, and how much of it. |
| `implication` | yes | **The so-what.** Theme plus evidence without an implication is not a finding, and it is the implication that makes a readout defensible. |
| `severity` | no | `high`, `medium`, `low`. Renders as a step meter **plus** the word — never colour alone. |
| `icon` | no | Must be a filename (without extension) in the active branding pack's `assets/iconography/`. Never invent one. |

### `recommendations`
| Item field | Required |
|---|---|
| `action` | yes |
| `rationale` | yes |
| `horizon` | no |
| `owner` | no |

### `roadmap` (alias: `timeline`)
| Section field | Required | Notes |
|---|---|---|
| `time_scale` | no | `auto`, `week`, `two-week`, or `month`. This is the semantic calendar resolution, not a visual layout instruction. `auto` lets the renderer derive a useful scale from the earliest start and latest end. |
| `phases` | yes | One to six phases. |

| Phase field | Required |
|---|---|
| `name` | yes |
| `window` | yes |
| `outcomes` | yes, at least one |
| `start` / `end` | no — ISO 8601 dates supplied together, with `end` on or after `start`. When present, they render as the phase's factual date range; `window` remains the human-readable fallback. |
| `summary` | no — a short statement of the phase's purpose. |
| `activities` | no — up to six `{ title, detail? }` entries describing what happens inside the phase. |
| `decision` | no — the decision or review point that closes or advances the phase. |
| `milestones` | no — up to four `{ title, date?, detail? }` entries. They render in a native disclosure so the primary timeline stays scannable while its decision points remain available. |

The delivery-approach module exposes one view over this payload:

- `execution_map` positions phases proportionally when every phase supplies
  `start` and `end`; otherwise it renders the supplied ordered phase sequence.
  A reader can move through the map by period and select a phase to inspect its
  supplied activities, outcomes, milestones, and decision point.

The execution map does not create week names, weekly goals, activities, dates,
milestones, decisions, or outcomes that are absent from the input.

#### Boundary from discovered context to rendering

The review inbox remains the evidence and approval surface. A module composer
maps approved context into this contract before HTML is rendered:

| Reviewed source signal | Roadmap field |
|---|---|
| Confirmed phase or workstream name | `name` |
| Confirmed start and end | `start`, `end` |
| Human-readable planning language | `window` |
| Supported description of intent | `summary` |
| Supported work within the phase | `activities` |
| Supported result | `outcomes` |
| Confirmed review or approval | `decision` or `milestones` |

The mapping step retains citations and dispositions in `intake.yaml`; the
presentation content contains only approved, typed values. The renderer does
not infer dates, activities, decisions, or time scale from prose.

### `quote`
| Field | Required | Notes |
|---|---|---|
| `quote` | yes | Straight quotes in the source become curly on output. |
| `name` | yes | Attribute by role, not by name, unless the speaker consented to be named. |
| `attribution_title` | no | Usually the organisation. |

### `heatmap`
| Field | Required | Notes |
|---|---|---|
| `title` | yes | |
| `columns` | yes, 1–4 | e.g. `[Current, Target]` |
| `rows` | yes | |

| Row field | Required | Notes |
|---|---|---|
| `capability` | yes | |
| `values` | yes | Integers 1–5, one per column. |
| `note` | no | A short qualifier under the capability. |

Every cell prints its numeral alongside a step meter, and the legend spells out
the 1–5 scale, so nothing depends on colour.

### `next-steps`
| Field | Required |
|---|---|
| `title` | no |
| `items` | yes — a list of short strings |

### `methodology`
| Field | Required |
|---|---|
| `title` | no |
| `body` | yes — prose |

### `agenda`
| Field | Required |
|---|---|
| `title` | no |
| `items` | yes, at least one |

Each item requires a short `title` and a `detail` explanation. Items render as
keyboard-accessible disclosure cards. Opening one item closes the previously
open item, keeping the agenda compact. The interaction uses native HTML and
remains usable without JavaScript.

### `table`
Generic column/row data — no rating or colour semantics. Reused across a
deck for team & roles, deliverables, a workshop plan, or key assumptions,
each with its own `columns`.

| Field | Required | Notes |
|---|---|---|
| `title` | yes | What this table is — unlike other sections, there is no useful fallback. |
| `columns` | yes, at least 1 | Column headers, in order. |
| `rows` | yes, at least 1 | |

| Row field | Required | Notes |
|---|---|---|
| `cells` | yes, at least 1 | One string per column, in order. The first cell is the row's header (e.g. a name or a deliverable), not just its first value. |

## Prose subset

`body` fields accept a small markdown subset:

- blank-line-separated paragraphs
- `- ` bullet lists
- `**bold**` and `*italic*`

Straight quotes and apostrophes become curly; ` -- ` becomes an em dash.
Everything else is escaped and rendered as literal text.

Client-visible generated prose uses standard American English unless the
consultant or client requests another convention. Preserve verbatim source
quotations when fidelity matters.

**External links are an error.** A client deliverable makes no network request,
so a link to `https://…` is refused at authoring time rather than discovered by
the validator after the build. Quote the source in text instead.

## Errors

Every problem is reported at once, each naming its location:

```
content is not valid:
  - meta: missing required field `classification`
  - sections[2].findings[0]: missing required field `implication` — theme +
    evidence without a so-what is not a finding; the implication is what makes
    a readout defensible
  - sections[4]: at most 4 items, found 5 — a KPI row past four tiles breaks
    both the layout and comprehension
```

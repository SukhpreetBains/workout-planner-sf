# Archetypes

An archetype is a pre-composed arrangement of the component kit: which sections
are allowed, which are required, the order they read best in, the chrome that
gets injected, and the default motion level. It adds no styling of its own.

Manifests live at `templates/<name>/archetype.json`, with a complete worked
example alongside at `content.example.yaml`.

## `project-kickoff`

The first client-facing session of an engagement: who is on the team, what
we are here to do, how we will work together, and what happens next. Sets
expectations rather than reporting findings.

| | |
|---|---|
| Cover surface | Slalom Blue (white logo, colour bar with the blue swatch at Dark 3) |
| Footer surface | Black |
| Required | `purpose`, `agenda`, `table`, `roadmap`, `next-steps` |
| Also allowed | `kpi-row`, `timeline`, `theme-group`, `heatmap`, `quote` |
| Injected | `cover`, `progress-rail`, `footer` |

Recommended order:

`purpose` → `agenda` → `table` (team & roles) → `roadmap` →
`table` (deliverables) → `theme-group` (risks) → `next-steps`

The reasoning behind the required set:

- **`purpose` opens the deck**, stating why the engagement exists and what
  is in scope. It is not `exec-summary` reused: the shape is identical
  (title + a lead prose block in the same emphasis box, implemented by the
  objectives-and-scope module), but a kickoff has no findings yet to
  summarize. `exec-summary`'s eyebrow and fallback title ("Summary" / "In
  brief") would misdescribe that, so `purpose` carries its own ("Purpose" /
  "Purpose & scope") over the same rendering.
- **`agenda` is required**, distinct from the progress rail. A live kickoff
  session opens with an explicit agenda by convention; the rail is a
  persistent nav for the scrolling page, not a replacement for it.
- **`table` is required at least once**, for team and roles. A kickoff that
  does not say who is on the team and what they own has not actually kicked
  off anything. `table` is a generic, reusable component — the same type
  covers deliverables, a workshop plan, or key assumptions elsewhere in the
  same deck, each with its own columns.
- **`roadmap` is required** for the approach and timeline, reusing
  the shared phase-and-outcome component. This is deliberately
  *not* a date-scaled Gantt chart — the kit does not have one, and a named
  sequence of phases with outcomes is enough to set expectations at kickoff.
  `timeline` (the alias) is allowed if a second, later-stage view is needed.
- **`theme-group` is allowed but optional**, reframed for risks rather than
  findings: `theme` is the risk, `evidence` is the description, `implication`
  is the response or mitigation, `severity` behaves the same way.
- **`next-steps` is required.** A kickoff that ends without a concrete
  action has reviewed expectations without setting any.

**Deliberately out of scope**: a generated org chart and team member photos.
Both appear in real kickoff decks, but photos are not an approved brand
asset in the sense `references/imagery.md` means, and an org-chart layout
component is a meaningfully larger addition than the rest of this archetype.
Represent reporting structure as another column in the team/roles `table`
instead (e.g. a "Reports to" column). Revisit as a dedicated component if a
deck genuinely needs the visual, not the data.

## Adding an archetype

1. `mkdir templates/<name>` and write `archetype.json`:

```json
{
  "name": "business-case",
  "title": "Business case",
  "description": "One paragraph on the audience and the decision it serves.",
  "cover_surface": "blue",
  "footer_surface": "black",
  "allowed_sections": ["exec-summary", "kpi-row", "recommendations", "roadmap", "next-steps"],
  "required_sections": ["exec-summary", "recommendations", "next-steps"],
  "recommended_order": ["exec-summary", "kpi-row", "recommendations", "roadmap", "next-steps"],
  "injects": ["cover", "progress-rail", "footer"],
  "default_motion": { "exec-summary": "fade-up" },
  "notes": ["Why this shape, in the author's words."]
}
```

2. Write a complete, realistic `content.example.yaml`. Realistic matters: a
   worked example with placeholder text teaches nothing about whether the
   archetype actually holds a real argument. Use a fictional client and say so.
3. Add a build test to `scripts/test/run.mjs`.

`cover_surface` and `footer_surface` must be surfaces the kit declares
(`white`, `blue`, `black`, `accent`), because the logo variant and the colour
bar's Dark 3 substitution are both derived from them.

Reach for a new archetype when the *argument shape* differs — a business case
leads with value, a roadmap leads with sequence, an assessment leads with a
scorecard. Do not create one just to reorder sections; `sections` is already
ordered by the author.

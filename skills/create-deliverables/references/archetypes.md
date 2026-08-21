# Archetypes

An archetype is a pre-composed arrangement of the component kit: which sections
are allowed, which are required, the order they read best in, the chrome that
gets injected, and the default motion level. It adds no styling of its own.

Manifests live at `templates/<name>/archetype.json`, with a complete worked
example alongside at `content.example.yaml`.

## `executive-readout`

Discovery findings for an executive audience. Reads top to bottom in ten minutes
and prints as a defensible record.

| | |
|---|---|
| Cover surface | Slalom Blue (white logo, colour bar with the blue swatch at Dark 3) |
| Footer surface | Black |
| Required | `exec-summary`, `theme-group`, `recommendations`, `next-steps` |
| Also allowed | `kpi-row`, `quote`, `heatmap`, `roadmap`/`timeline`, `methodology` |
| Injected | `cover`, `progress-rail`, `footer` |

Recommended order:

`exec-summary` → `kpi-row` → `theme-group` → `quote` → `heatmap` →
`recommendations` → `roadmap` → `next-steps` → `methodology`

The reasoning behind the required set:

- **`exec-summary` first.** An executive who reads one block reads that one.
- **`theme-group` and `recommendations` are both required** because a readout
  that observes without recommending is a status report, and one that recommends
  without evidence is an opinion.
- **`next-steps` is required** because a readout that ends without an ask
  produces no decision.
- **`methodology` sits last.** It is the defensibility appendix, not the
  argument.

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

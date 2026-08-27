# Component kit

Brand-locked primitives. Archetypes are pre-composed arrangements of these, not
a second layer of styling.

Every component is a pure function `(section, ctx) => htmlString` in
`../scripts/lib/components.mjs`, registered by section type. Every one:

- emits semantic HTML
- declares motion with a `data-motion` attribute and contains no animation code
- carries no inline colour and no inline style
- **renders visible.** Nothing in `components.css` sets `opacity: 0`; the motion
  layer applies its own "before" state at init, so the deliverable is fully
  readable with JavaScript disabled or blocked.

| Component | Purpose | Default motion |
|---|---|---|
| `cover` | Client, title, date, logo, optional client lockup, colour bar, classification | `color-bar-draw` + `line-draw` |
| `progress-rail` | Sticky section progress — an executive needs to see the length | `scroll-sync` |
| `exec-summary` | The "if you read one thing" block | `fade-up` |
| `kpi-row` | 2–4 stat tiles | `count-up` (staggers and counts) |
| `finding-card` | theme → evidence → implication. The core unit. | `stagger-up` |
| `theme-group` | Titled cluster of finding cards | `stagger-up` |
| `quote` | Client voice | `fade-up` |
| `heatmap` | Capability ratings, current against target | `cell-sweep` |
| `roadmap` / `timeline` | Phases, windows, outcomes | `path-draw` |
| `recommendations` | Prioritised actions with owner and horizon | `stagger-up` |
| `next-steps` | Short closing list | `stagger-up` |
| `methodology` | What was reviewed and who was spoken to, in aggregate | none |
| `footer` | Logo, classification, prepared-for, date | none |

`cover`, `progress-rail` and `footer` are injected by the archetype.
`finding-card` is composed by `theme-group` rather than authored directly.

## The surface contract

This is the part to understand before touching the CSS.

A **surface** is a background paired with the text colours approved to sit on
it. `tokens.css` declares four:

| Surface | Background | Text tokens |
|---|---|---|
| `surface-white` | White | `--on-white-body` (black), `--on-white-display` (Slalom Dark Blue), `--on-white-muted` (Dark Gray), `--on-white-emphasis` (Slalom Blue) |
| `surface-blue` | Slalom Blue | `--on-blue-body`, `--on-blue-display` (both white) |
| `surface-black` | Black | `--on-black-body`, `--on-black-display` (both white) |
| `surface-accent` | `var(--accent)` | `--on-accent-body`, `--on-accent-display` (both black) |

Two rules the validator enforces:

1. **A rule that paints a background must pair a text colour from the same
   surface**, or carry a trailing `/* no-text */` comment declaring that it holds
   no text (a swatch, a meter step, a rule).
2. **A `color` declaration must use an `--on-<surface>-*` token**, or
   `currentColor` / `inherit`. That is what keeps every pair on the page
   checkable against the approved-combination table and against WCAG contrast.

Black text is the one treatment approved on all four secondaries, and it clears
4.5:1 on every one of them, which is why `surface-accent` is uniform.

Two brand-approved pairs are deliberately absent because they fail WCAG AA:
purple on Slalom Blue (2.85:1) and cyan on Slalom Blue (3.18:1). Where the brand
and the accessibility floor disagree, the floor wins and the pair goes unused.

## Component notes

**`cover`** — the logo variant follows the surface: blue, dark blue or black
background takes the white mark; white, light or secondary takes the blue mark.
Clear space is at least the width of an "o" (0.428 × the logo height on the
216 × 56.1 viewBox), applied as padding with a negative margin so it does not
push the layout around. A client logo forms a partner lockup separated by a
rule, never larger than the Slalom mark. Read
the active branding pack's `logo.md` (see `../../utilities-ui-generation/references/branding.md`) before repositioning either.

**`kpi-row`** — `value` may be non-numeric, in which case `count-up` degrades to
a plain render because the builder simply omits `data-count-to`. The source line
always shows.

**`finding-card`** — severity renders as a three-step meter *plus* the word
"High" / "Medium" / "Low". The colour is decoration on top of a label that
already works in greyscale and in print. At wide viewports evidence and
implication sit side by side rather than leaving the card half empty.

**`heatmap`** — a white cell carrying a five-step meter and the numeral, not a
coloured cell. Colour never carries the value, the legend spells out the scale,
and it prints and photocopies correctly.

**`quote`** — Slalom Sans only: Regular for the quote, Bold for the name, Light
for the title. Both approved pairings in `typography.md` want a supporting
serif, and no serif ships with this repo, so neither can be fully satisfied. The
validator raises this as a known deviation on every build that includes a quote.
See `delivery.md`.

**`progress-rail`** — keyboard navigable with a visible focus ring, marks the
current section with `aria-current`, hidden in print. Under reduced motion the
scroll-linked fill is removed rather than frozen at zero, because an empty
progress bar is worse than none.

## Adding a component

1. Add its schema to `SECTION_SCHEMA` in `scripts/lib/content.mjs`. Required
   fields are the place to encode editorial standards — `implication` is
   required for a reason.
2. Add the render function to `COMPONENTS` in `scripts/lib/components.mjs`.
   Semantic HTML, a `data-motion` attribute, no inline colour.
3. Add its styles to `components.css` using existing tokens. If you need a value
   that is not a token, add the token to `tokens.css` — that is the only file
   allowed to hold a literal.
4. Add the type to the relevant `archetype.json` `allowed_sections`.
5. Add a case to `scripts/test/run.mjs` and rebuild the worked example.

If a component needs a colour that is not in the palette, or a text pair that is
not in the approved table, the answer is a different design — not a new token.

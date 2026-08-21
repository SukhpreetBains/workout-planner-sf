# Layout system

Everything here lives in `assets/css/tokens.css`, which is the only file in a
built deliverable permitted to contain a literal value for colour, size, or
spacing. The validator parses the allowed palette out of it at runtime, so the
palette has exactly one source of truth.

## Grid

| Token | Value | Use |
|---|---|---|
| `--page-max` | `68rem` | Content column |
| `--page-gutter` | `--space-4` | Page inset, tightening on small screens |
| `--measure` | `34rem` | Body copy line length |

Sections are full-bleed surfaces with an inner `--page-max` column. Card grids
use `repeat(auto-fit, minmax(…, 1fr))` so a three-phase roadmap and a
five-recommendation list both lay out without per-count rules.

## Spacing scale

`--space-1` `0.25rem` · `--space-2` `0.5rem` · `--space-3` `1rem` ·
`--space-4` `1.5rem` · `--space-5` `2.5rem` · `--space-6` `4rem` ·
`--space-7` `6rem`

`--space-7` is the section rhythm and drops to `3.5rem` under 40rem wide. Use the
scale; a one-off `13px` is how a layout starts drifting.

## Type scale

| Token | Size | Role | Weight |
|---|---|---|---|
| `--size-display` | `clamp(2.5rem, 6vw, 4.5rem)` | Cover title | 900 Black |
| `--size-kpi` | `clamp(3rem, 7vw, 5rem)` | Stat figures | 900 Black |
| `--size-h2` | `clamp(1.75rem, 3.2vw, 2.5rem)` | Section headline, pull quote | 700 Bold |
| `--size-h3` | `1.25rem` | Subhead, cover subtitle | 700 Bold |
| `--size-body` | `1.0625rem` | Body copy | 300 Light |
| `--size-small` | `0.875rem` | Captions, sources, rail | 400 Regular |
| `--size-eyebrow` | `0.75rem` | All-caps labels | 700 Bold, tracked `0.075em` |

Slalom Sans ships in four weights here — 300, 400, 700, 900. There is no Medium
or SemiBold in the family, `font-synthesis: none` stops the browser inventing
one, and the validator errors on any weight outside the shipped set.

### Setting type

Sentence case throughout. All caps only for a short eyebrow label, never a
sentence, and always tracked out. Flush left, ragged right — never justified,
never centred. `text-wrap: balance` on headlines and `pretty` on body copy do
the widow and orphan work that a print designer would do by hand.

### Two deliberate deviations from the print guidance

**Leading.** The brand's starting points are 0.90 for headlines and 1.1 for body,
which are print figures. 1.1 is unreadable for on-screen prose at a 34rem
measure, so body copy opens to `1.55` while display type stays tight at `0.95`.
WCAG 1.4.12 also expects content to survive a reader forcing 1.5 line height;
starting there means nothing breaks when they do.

**Three type sizes per composition.** The brand asks for at most three where
practical. A scrolling web readout legitimately carries four in most sections:
a headline, body copy, a small caption or source line, and an eyebrow label.
Validator rule 12 reports this as a single warning naming the sections and their
counts. Treat it as a prompt to check whether a fifth size crept in, not as
something to eliminate — but do read it, because a fifth size usually means
someone added a one-off.

## Shapes

**Exactly one rounded corner.** `--corner` is `1.25rem`, matched to the "l" in
the logo, and applied to one corner only:

```css
border-radius: var(--corner) 0 0 0;   /* finding, recommendation */
border-radius: 0 var(--corner) 0 0;   /* exec summary */
border-radius: 0 0 0 var(--corner);   /* KPI tile */
border-radius: 0 0 var(--corner) 0;   /* roadmap phase */
```

Never round every corner by default. Rectangles and fluid waves are the other
approved shapes; decorative gradients are not.

## Brand element geometry

| Token | Constraint |
|---|---|
| `--logo-height` | `2rem`. The brand minimum is 9px; the validator enforces it. |
| `--logo-clear-space` | `calc(var(--logo-height) * 0.45)`. Must be at least `0.428 ×` the height — the width of an "o" is roughly 24 of the 216 logo units on a 56.1-unit height. |
| `--color-bar-height` | `0.75rem`. One bar per layout, never more than 20% of it. |
| `--cover-min-height` | `100vh`, `auto` under 40rem so a phone does not get a screen of empty blue. |

## Print

`print.css` is linked in every build and the validator checks that it resolves
every animated element to its final state. It also:

- prints at US Letter portrait with 16/14 mm margins
- breaks the page after the cover
- keeps a unit of meaning — a finding, a KPI tile, a phase — on one page
- forces `print-color-adjust: exact` on the cover, footer, colour bar and meters,
  since the classification marker and the severity indicators depend on them
- drops the progress rail, the skip link and the Slalom line

Print to PDF before every handoff. A readout that looks right on screen and
loses a section on paper is a readout that gets forwarded broken.

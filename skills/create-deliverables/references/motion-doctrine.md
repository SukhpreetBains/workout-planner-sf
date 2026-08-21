# Motion doctrine

A client deliverable is not a marketing site. Motion earns its place by aiding
comprehension — signalling structure, drawing the eye to a figure, marking
position in a long document. Everything else is noise in a room where someone is
deciding whether to spend money.

`assets/js/motion.js` exports `initMotion(root)`, which reads `data-motion`
attributes and applies the matching recipe. Components declare motion; they never
contain animation code.

## Vocabulary

| Name | Recipe |
|---|---|
| `fade-up` | `y: [24, 0]`, `opacity: [0, 1]`, `outExpo`, 600 ms, on scroll, once |
| `stagger-up` | as above with `delay: stagger(80)` across the marked items |
| `color-bar-draw` | per-swatch `scaleX: [0, 1]`, origin left, `outExpo`, 500 ms, `stagger(90)` — in the fixed brand order |
| `line-draw` | `svg.createDrawable` on the Slalom line, `inOutQuad`, 1200 ms |
| `count-up` | staggers the tiles, then interpolates each numeral, `outExpo`, 900 ms |
| `cell-sweep` | grid stagger across heatmap cells, `outQuad`, 400 ms |
| `path-draw` | timeline: the roadmap path draws, then the phase cards stagger up |
| `scroll-sync` | `onScroll({ sync: true })` bound to the progress rail |

## Restraint rules

- **Reveal once.** Never re-animate on scroll back. An executive scrolling up to
  re-read a number must not watch it count again.
- Nothing under 250 ms or over 800 ms, except `line-draw` at 1200 ms on the cover.
- No parallax. No ambient loops in the body.
- **Motion never carries meaning alone** — the same principle as colour.
- `prefers-reduced-motion: reduce` **applies every final state immediately**
  rather than skipping the animation. Skipping an animation whose "before" state
  was already applied is how a page like this ends up permanently invisible for
  the one reader who most needed it not to move.

The two brand-native flourishes are `color-bar-draw` and `line-draw`: the bar
order is a rule the brand already specified, and the Slalom lines reference the
fluidity of the logo. Everything else is generic reveal motion — keep it quiet.

## Three safety nets, and why each exists

**Content is never hidden by CSS.** `components.css` contains no `opacity: 0`.
`motion.js` sets its own before-state at init, so with JavaScript disabled,
blocked, or still loading, the whole deliverable reads.

**`count-up` does not overwrite the real figure until it starts.** The tempting
implementation writes `0` into the DOM at init and animates upward. That prints
`0%` on every tile the reader had not yet scrolled to — the animation quietly
destroying the content it was decorating. Instead the real number stays until the
animation is actually triggered, and a `beforeprint` handler forces every figure
to its final value.

**A watchdog reveals anything left invisible.** If the scroll observer never
fires for an element in the viewport — a stale browser, a blocked API, a layout
with no scroll range — the element is revealed 2.5 seconds after init. A recipe
that throws reveals its subtree immediately. One bad animation must never leave a
client staring at empty space.

## Adding a recipe

1. Add a quoted key to `RECIPES` in `assets/js/motion.js`, one per line — the
   test suite and the validator both read that list to prove every `data-motion`
   value the builder can emit has a recipe.
2. Apply the before-state inside the recipe with `utils.set`, never in CSS.
3. Add a final state to the `prefers-reduced-motion` block in `components.css`
   and to `print.css` if the recipe touches anything other than `opacity` and
   `transform` — a drawn stroke needs `stroke-dashoffset: 0`, for instance.
4. Stay inside the duration bounds above.

For anything outside this vocabulary, invoke the `animejs` skill: it owns the
Anime.js v4 API surface, and `../../animejs/references/` covers easings, stagger,
scroll observers, and SVG drawing in detail. Come back with a recipe, not with
animation code inside a component.

## Loading

The deliverable imports Anime.js through an import map so that snippets from the
`animejs` skill's references paste in unchanged:

```html
<script type="importmap">{"imports":{"animejs":"./js/anime.esm.min.js"}}</script>
```

Subpath imports (`animejs/svg`) are a bundler feature and do not work from this
bundle — take every export from the single file.

Browsers refuse to fetch ES modules over `file://`, so the folder build needs a
local server to show motion (`python3 -m http.server 8000`). The `--bundle`
output points the import map at a data URL and therefore runs straight off disk.

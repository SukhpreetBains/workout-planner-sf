---
name: animejs
description: "Use when the user wants to add animation or motion to an HTML page or web app - entrances/reveals, hover & press micro-interactions, scroll-triggered effects, loaders, looping ambient motion, draggable UI, SVG line-drawing/morphing, or animated text - built with Anime.js (v4). This skill first asks what they want to animate and helps design it, then writes the code. Prefer v4 named imports (`import { animate } from 'animejs'`), never the v3 default export `anime({ targets })`. Not for CSS-only transitions or other libraries (GSAP, Framer Motion, Motion One)."
---

# Anime.js (v4) - design & build web animations

This skill helps you **design** an animation with the user and then **build** it correctly with
Anime.js v4. Do not jump straight to code. Lead with a short discovery conversation so the user
keeps creative control, propose a concrete design, then implement it.

Anime.js **v4 is a rewrite of v3**. It removed the single default `anime()` export in favor of
**named, tree-shakeable exports**. Never emit v3 syntax (`anime({ targets, ... })`,
`anime.stagger`, `easeInOutQuad`). See `references/core-api.md` for the v3→v4 mapping.

## Step 1 - Discover (ask before building)

Ask the user a few pointed questions so *they* drive the creative direction. Use the
`AskUserQuestion` tool when it fits; otherwise ask inline. Keep it to the essentials:

1. **What element(s)?** - hero heading, a card/grid, nav, a button, an SVG logo, a loader, a
   full-page intro, an image, a list.
2. **What kind of motion / feel?** - entrance/reveal · hover or press micro-interaction ·
   scroll-tied · continuous/ambient loop · draggable · SVG line-draw or morph · text animated
   character-by-character.
3. **What triggers it?** - on page load · when it scrolls into view · on hover/click ·
   continuously.
4. **Personality?** - snappy · smooth · bouncy/springy · dramatic. (This maps to concrete
   easing/duration/stagger values - see the recipe table below.)
5. **Setup context?** - plain HTML file with no build step · a bundler (Vite/webpack) · a
   framework (React/Vue). This routes to the right recipe in `references/setup.md`.

If the user already gave enough of this in their request, skip ahead - don't interrogate.

## Step 2 - Propose a design

Turn the answers into one concrete, plain-language proposal, e.g.:

> "Staggered fade-up of the 6 cards: each rises 24px and fades in over 600ms with an
> `outExpo` ease and an 80ms stagger, triggered when the grid scrolls into view."

Offer 1–2 tasteful variations (e.g. "or a springy scale-in instead of fade-up"), and confirm
before writing code. This is where the user exercises creative autonomy.

### Personality → recipe (starting points, tune to taste)

| Personality | ease | duration | stagger | notes |
|---|---|---|---|---|
| **Snappy** | `'outQuad'` / `'outExpo'` | 250–450ms | 30–60ms | crisp UI, buttons, menus |
| **Smooth** | `'inOutQuad'` / `'inOutCirc'` | 500–800ms | 60–100ms | elegant reveals |
| **Bouncy** | `createSpring({ stiffness: 120, damping: 8 })` or `'outBack'` | spring-driven | 60–120ms | playful, draggable release |
| **Dramatic** | `'outExpo'` / `'outElastic(1, .4)'` | 800–1400ms | 100–200ms | hero intros, big statements |

Respect `prefers-reduced-motion` - see `references/frameworks.md` (`createScope` media queries).

## Step 3 - Build

Emit correct v4 code for the agreed design, wire up the trigger, and (in a framework) add
cleanup. Then point the user at the relevant reference file for tuning. Confirm setup first: if
the library isn't installed/linked, follow `references/setup.md`.

### v4 API cheat sheet

```js
import {
  animate, createTimer, createTimeline, createAnimatable, createScope,
  createDraggable, onScroll, stagger, svg, text, utils, eases, createSpring, engine
} from 'animejs';

animate('.box', { x: 320, rotate: '1turn', duration: 800, ease: 'outExpo' });   // core
createTimer({ duration: 1000, loop: true, onUpdate: self => {} });               // raw ticker
createTimeline().add('.a', { x: 100 }).add('.b', { x: 100 }, '<');              // sequencing
createDraggable('.card', { container: '#box' });                                // drag
animate('.reveal', { y: [24, 0], opacity: [0, 1],                               // scroll trigger
  autoplay: onScroll({ enter: 'bottom top', sync: true }) });
animate('.item', { scale: [0, 1], delay: stagger(80, { from: 'center' }) });    // stagger
```

### Golden rules

- **Targets** accept a CSS selector, DOM element, NodeList, JS object, or an array of these.
- **Property keys** are camelCase transforms (`x`, `y`, `rotate`, `scale`, `skew`) and CSS
  props (`opacity`, `backgroundColor`, `borderRadius`). `x`/`y` are shorthands for
  `translateX`/`translateY`.
- **Values** can be a number, a unit string (`'20rem'`, `'50%'`), relative (`'+=50'`), a color,
  a `[from, to]` array, a per-property keyframe array, or a function `(el, i, len) => value`.
- **Eases** use v4 names without the `ease` prefix: `'linear'`, `'inOutQuad'`, `'outExpo'`,
  `'outBack'`, `'outElastic(1, .3)'`, or `createSpring({...})`. See `references/easings-stagger-utils.md`.
- **Framework code must clean up**: wrap animations in `createScope` and call `scope.revert()`
  on unmount. See `references/frameworks.md`. This is the #1 real-world footgun.
- **Never** use v3 `anime({ targets })`, `anime.timeline()`, or `anime.stagger()`.

## References (load on demand)

- `references/setup.md` - install via npm, CDN (no-build ESM), the vendored offline copy, bundler
  subpaths, TypeScript.
- `references/core-api.md` - `animate`, `createTimer`, `createTimeline`, params, callbacks,
  keyframes, value types, playback control, and the full **v3→v4 mapping**.
- `references/interaction.md` - `createDraggable`, `onScroll` (scroll observer), `createAnimatable`.
- `references/svg-text.md` - `svg.morphTo` / `createDrawable` / `createMotionPath`; `splitText` /
  `scrambleText`.
- `references/easings-stagger-utils.md` - all easings, `createSpring`, `stagger` (grid/axis/from),
  `utils` (math + random), `engine` globals.
- `references/frameworks.md` - React (`useEffect`), Vue (`onMounted`/`onUnmounted`), and vanilla
  cleanup with `createScope`, plus `prefers-reduced-motion`.

## Verify

Open `assets/demo.html` in a browser - it uses the CDN-ESM import and shows a staggered timeline
with no build step, doubling as a working reference you can crib from.

## Offline / no external requests

`assets/vendor/` holds a pinned v4.5.0 ESM bundle (MIT) for pages that must work offline or make no
external requests - client deliverables especially. Copy the bundle and its `LICENSE.md` alongside
the page and import it relatively. Details in [assets/vendor/README.md](assets/vendor/README.md).

## Source

Anime.js v4 documentation: https://animejs.com/documentation/ · v3→v4 migration:
https://github.com/juliangarnier/anime/wiki/Migrating-from-v3-to-v4

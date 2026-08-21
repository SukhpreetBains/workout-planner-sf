# Setup - installing & wiring Anime.js v4

Pick the recipe that matches the project. When unsure, ask: "Is this a plain HTML file, or a
project with a bundler / framework?"

## Which recipe do I need?

| Situation | Recipe |
|---|---|
| A single `.html` file, no build tooling | **CDN (ESM)** |
| Must work offline, or ship with no external requests | **Vendored local copy** |
| Vite / webpack / Rollup / Parcel project | **npm** |
| React / Vue / Svelte component | **npm** + `references/frameworks.md` |
| Care about bundle size | **npm + subpath imports** |

## npm (bundlers & frameworks)

```bash
npm install animejs
# types ship with the package - no @types/animejs needed for v4
```

```js
import { animate, createTimeline, stagger, utils } from 'animejs';

animate('.box', { x: 320, ease: 'outExpo', duration: 800 });
```

### Subpath imports (better tree-shaking)

Import only the module you use so bundlers can drop the rest:

```js
import { animate }         from 'animejs/animation';
import { createTimeline }  from 'animejs/timeline';
import { createTimer }     from 'animejs/timer';
import { createScope }     from 'animejs/scope';
import { createDraggable } from 'animejs/draggable';
import { onScroll }        from 'animejs/scroll';
import { stagger }         from 'animejs/stagger';
import { eases, createSpring, cubicBezier } from 'animejs/easings';
import { morphTo, createDrawable, createMotionPath } from 'animejs/svg';
import { splitText, scrambleText } from 'animejs/text';
import { utils }           from 'animejs/utils';
```

## CDN - no build step (ESM)

In a plain HTML file, use a `type="module"` script and import directly from a CDN. This is the
fastest way to try something and is what `assets/demo.html` uses.

```html
<script type="module">
  import { animate, stagger } from 'https://cdn.jsdelivr.net/npm/animejs/+esm';

  animate('.box', {
    y: [40, 0],
    opacity: [0, 1],
    delay: stagger(80),
    ease: 'outExpo',
    duration: 700,
  });
</script>
```

Pin a version for stability, e.g. `https://cdn.jsdelivr.net/npm/animejs@4/+esm`.

### Import maps (cleaner CDN imports)

```html
<script type="importmap">
  { "imports": { "animejs": "https://cdn.jsdelivr.net/npm/animejs@4/+esm" } }
</script>
<script type="module">
  import { animate } from 'animejs';
  animate('.box', { x: 200 });
</script>
```

## Vendored local copy - no build step, no network

`assets/vendor/anime.esm.min.js` is a pinned v4 bundle committed to this skill. Reach for it over
the CDN whenever the page must work offline, or is a client-facing artifact that should make no
external requests. Copy the bundle **and `LICENSE.md`** next to the page — MIT requires the notice
travel with the code.

```html
<script type="importmap">
  { "imports": { "animejs": "./vendor/anime.esm.min.js" } }
</script>
<script type="module">
  import { animate, stagger } from 'animejs';
  animate('.box', { y: [40, 0], opacity: [0, 1], delay: stagger(80), ease: 'outExpo' });
</script>
```

The import map is worth the two extra lines: every snippet in these references imports from
`'animejs'`, so they paste in unchanged. A plain relative import
(`from './vendor/anime.esm.min.js'`) works just as well.

One difference from npm: **subpath imports like `animejs/svg` do not work here.** They are a
bundler feature. Take every export from the single bundle. See
[assets/vendor/README.md](../assets/vendor/README.md) for the version, hashes, and update steps.

## TypeScript

Types are bundled with the package in v4 - no separate `@types` install. Named imports are
fully typed:

```ts
import { animate, type JSAnimation } from 'animejs';
const a: JSAnimation = animate('.box', { x: 100 });
```

## Sanity check

After wiring, a one-line `animate('body', { opacity: [0.5, 1], duration: 300 })` in the console
(or a temporary call) should visibly run. If nothing happens, confirm the import path resolved
and the target selector matches a real element that exists when the code runs.

## Source

- Getting started / imports: https://animejs.com/documentation/getting-started/imports/
- Module imports: https://animejs.com/documentation/getting-started/module-imports/

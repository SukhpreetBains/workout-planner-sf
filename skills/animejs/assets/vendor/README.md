# Vendored Anime.js

A local copy of Anime.js so a page can animate with **no build step and no external network request**. Use this instead of the CDN whenever the output is a client deliverable, has to work offline, or must not phone out.

| | |
|---|---|
| Version | v4.5.0 |
| License | MIT — Julian Garnier ([LICENSE.md](LICENSE.md)) |
| Source | `https://registry.npmjs.org/animejs/-/animejs-4.5.0.tgz`, `dist/bundles/` |

| File | Size | Use |
|---|---|---|
| `anime.esm.min.js` | 116 KB | Ship this. Production and every deliverable. |
| `anime.esm.js` | 399 KB | Readable source for debugging an animation locally. Never ship it. |

MIT requires the copyright and permission notice travel with the code, so **copy `LICENSE.md` alongside the bundle** wherever it goes.

## Use it

Relative import from a plain HTML file:

```html
<script type="module">
  import { animate, stagger } from './vendor/anime.esm.min.js';

  animate('.card', { y: [24, 0], opacity: [0, 1], delay: stagger(80), ease: 'outExpo', duration: 600 });
</script>
```

An import map keeps `'animejs'` bare, so snippets copied from the references need no rewriting:

```html
<script type="importmap">
  { "imports": { "animejs": "./vendor/anime.esm.min.js" } }
</script>
<script type="module">
  import { animate } from 'animejs';
</script>
```

The bundle carries every named export in the SKILL.md cheat sheet — `animate`, `createTimer`, `createTimeline`, `createAnimatable`, `createScope`, `createDraggable`, `onScroll`, `stagger`, `svg`, `text`, `utils`, `eases`, `createSpring`, `engine` — plus `svg.createDrawable` / `svg.morphTo` / `svg.createMotionPath` and `text.splitText` / `text.scrambleText`. Subpath imports (`animejs/svg`) are a **bundler-only** feature and do not work here; take everything from the one bundle.

## Verify

```sh
shasum -a 256 anime.esm.min.js
# a19015a1a92d52025a2fb6703b6d67eadd1cc2aeaf880770e96e04cf6aa07be1

shasum -a 256 anime.esm.js
# a88ebfb5bd290f25215692edce71a74c0fc37bdb9e0ff70bd17135c5c3ef33b6
```

Confirm the exports still resolve after any update:

```sh
node --input-type=module -e "import * as a from './anime.esm.min.js'; console.log(Object.keys(a).length)"
```

## Update

```sh
curl -sL https://registry.npmjs.org/animejs/-/animejs-<version>.tgz | tar -xz
cp package/dist/bundles/anime.esm.min.js package/dist/bundles/anime.esm.js .
cp package/LICENSE.md .
```

Then refresh the version, sizes, and hashes above, and re-run the export check. Pin an exact version — never track a range.

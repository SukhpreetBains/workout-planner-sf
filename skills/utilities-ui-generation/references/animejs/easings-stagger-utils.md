# Easings, stagger & utilities

## Easings

Pass to any `ease` param as a **string name** (v4 dropped the `ease` prefix) or a **function**.

```js
import { animate, eases, cubicBezier, createSpring } from 'animejs';
// or: import { eases, cubicBezier, createSpring } from 'animejs/easings';

animate('.a', { x: 100, ease: 'inOutQuad' });          // string name
animate('.b', { x: 100, ease: 'out(3)' });             // parameterized power ease
animate('.c', { x: 100, ease: 'outElastic(1, .3)' });  // elastic(amplitude, period)
animate('.d', { x: 100, ease: cubicBezier(.7, .1, .5, .9) });
animate('.e', { x: 100, ease: createSpring({ stiffness: 120, damping: 8 }) });
```

### Built-in names

Base functions, each with `in` / `out` / `inOut` variants:

`linear`, `inQuad`/`outQuad`/`inOutQuad`, `inCubic`…`inOutCubic`, `Quart`, `Quint`, `Sine`,
`Expo`, `Circ`, `Back` (overshoot), `Bounce`, `Elastic`.

Parameterized: `'in(p)'` / `'out(p)'` / `'inOut(p)'` (power), `'outElastic(amplitude, period)'`,
`'inBack(overshoot)'`, `steps(n)`, `'irregular(length, randomness)'`, `linear(...)` with stops.

### Springs - `createSpring`

Physics-based; duration is derived from the physics, not set.

```js
createSpring({ mass: 1, stiffness: 100, damping: 10, velocity: 0 });
createSpring({ stiffness: 200, damping: 8 });   // snappy
createSpring({ stiffness: 80,  damping: 5 });   // bouncy
```

Great for draggable `releaseEase` and playful UI. See the personality table in `SKILL.md`.

## `stagger(value, options?)`

Distributes a value (usually `delay`, but any property) across multiple targets.

```js
import { animate, stagger } from 'animejs';

animate('.item', { y: [24, 0], delay: stagger(80) });                 // 80ms between each
animate('.item', { y: [24, 0], delay: stagger(80, { from: 'center' }) });
animate('.item', { scale: stagger([0.6, 1]) });                      // spread a value range
animate('.item', { delay: stagger(80, { start: 300, ease: 'inOut' }) });
```

Options:

| Option | Values |
|---|---|
| `from` | `'first'` (default), `'last'`, `'center'`, or an index number |
| `start` | base offset added to every value |
| `ease` | distribute non-linearly (name or function) |
| `reversed` | reverse the order |
| `grid` | `[columns, rows]` - stagger in 2D |
| `axis` | `'x'` or `'y'` - restrict grid staggering to one axis |

```js
// 2D grid ripple from the center
animate('.cell', { scale: [0, 1], delay: stagger(40, { grid: [14, 5], from: 'center' }) });
```

## `utils` - math & random helpers

```js
import { utils } from 'animejs';

// DOM read/write
utils.get('.box', 'x');          // read a current value
utils.set('.box', { opacity: 0 }); // set without animating
utils.remove('.box');            // stop/remove animations on targets

// Math (many are chainable)
utils.clamp(v, 0, 100);
utils.round(v, 2);
utils.snap(v, 10);
utils.wrap(v, 0, 360);
utils.mapRange(v, 0, 1, 0, 100);
utils.lerp(a, b, 0.5);
utils.damp(a, b, 0.1, dt);

// Random
utils.random(0, 100);            // random in range
utils.random(0, 100, 2);         // with decimals
utils.randomPick(['a', 'b', 'c']);
utils.shuffle(array);
const rng = utils.createSeededRandom(42);   // deterministic

// Chaining
const clean = utils.clamp(0, 100).round(0);   // reusable composed function
```

## `engine` - global configuration

```js
import { engine } from 'animejs';

engine.timeUnit = 's';     // use seconds instead of ms for all durations/delays
engine.speed = 2;          // global speed multiplier
engine.fps = 60;           // cap frame rate
engine.precision = 4;      // rounding precision
engine.pause();            // pause / resume the whole engine
engine.resume();
```

## Source

- Easings: https://animejs.com/documentation/easings/
- Stagger: https://animejs.com/documentation/stagger/
- Utilities: https://animejs.com/documentation/utilities/
- Engine: https://animejs.com/documentation/engine/

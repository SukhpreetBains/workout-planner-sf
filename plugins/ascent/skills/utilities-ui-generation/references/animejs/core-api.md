# Core API - animate, timer, timeline

## `animate(targets, parameters)`

The workhorse. Returns a `JSAnimation` with control methods.

```js
import { animate } from 'animejs';

const anim = animate('.box', {
  x: 320,               // translateX shorthand
  rotate: '1turn',
  scale: [0.8, 1],      // [from, to]
  backgroundColor: '#4f46e5',
  duration: 800,
  delay: 100,
  ease: 'outExpo',
  loop: false,
  onComplete: self => console.log('done'),
});
```

### Targets

CSS selector string · DOM element · `NodeList` / array of elements · a plain JS object (animate
its numeric props) · an array mixing these.

```js
const state = { count: 0 };
animate(state, { count: 100, duration: 1000, onUpdate: () => render(state.count) });
```

### Animatable properties

CSS properties (`opacity`, `backgroundColor`, `borderRadius`, `width`…), CSS transforms
(`x`/`y`/`z`, `translateX`, `rotate`, `scale`, `skew`), CSS variables, HTML/SVG attributes, and
plain JS object properties. `x`/`y` are shorthands for `translateX`/`translateY`.

### Tween value types

```js
animate('.box', {
  opacity: 1,                         // number
  width: '100px',                     // unit string
  x: '+=50',                          // relative to current
  backgroundColor: '#ff0000',         // color (hex/rgb/hsl)
  rotate: [0, '1turn'],               // [from, to]
  delay: (el, i, len) => i * 100,     // function per target
  y: [                                // per-property keyframes (v4 uses `to`)
    { to: '-2.75rem', ease: 'outExpo', duration: 600 },
    { to: 0, ease: 'outBounce', duration: 800, delay: 100 },
  ],
});
```

### Playback settings

| Param | Meaning |
|---|---|
| `duration` | ms (default 1000) |
| `delay` | initial delay ms (accepts a function or `stagger()`) |
| `loop` | `true` (infinite), a number, or `false` |
| `loopDelay` | ms between loops |
| `alternate` | reverse direction each loop |
| `reversed` | start reversed |
| `autoplay` | `true` (default), `false`, or `onScroll({...})` |
| `playbackRate` | speed multiplier |
| `frameRate` | cap update FPS |
| `ease` | easing (see `easings-stagger-utils.md`) |

### Callbacks

`onBegin`, `onBeforeUpdate`, `onUpdate`, `onRender`, `onLoop`, `onComplete`, `onPause` - each
receives the animation instance (`self`), e.g. `self.progress`, `self.currentTime`.

### Control methods

`play()`, `pause()`, `resume()`, `reverse()`, `restart()`, `seek(ms)`, `complete()`, `reset()`,
plus the `.then()` promise-like `onComplete`.

## `createTimer(parameters)`

A raw ticker with no targets - for counters, clocks, or driving custom render logic.

```js
import { createTimer } from 'animejs';

createTimer({
  duration: 1000,
  loop: true,
  frameRate: 30,
  onUpdate: self => console.log(self.currentTime),
  onLoop:   self => console.log('looped'),
  onComplete: () => console.log('done'),
});
```

Same playback controls as `animate` (`play`/`pause`/`seek`/`restart`…).

## `createTimeline(parameters)`

Sequences multiple animations with precise positioning.

```js
import { createTimeline } from 'animejs';

const tl = createTimeline({ defaults: { duration: 750, ease: 'outExpo' } });

tl.label('start')
  .add('.square',   { x: '15rem' }, 500)          // absolute: at 500ms
  .add('.circle',   { x: '15rem' }, 'start')      // at a label
  .add('.triangle', { x: '15rem', rotate: '1turn' }, '<-=500'); // relative to prev start
```

### Position values (3rd arg of `.add`)

| Form | Meaning |
|---|---|
| `500` | absolute time (ms) |
| `'+=200'` / `'-=200'` | relative to end of timeline |
| `'<'` | start at the **start** of the previous animation |
| `'<<'` | at the start of the timeline |
| `'label'` | at a named label |
| `'<-=500'` / `'<+=500'` | offset relative to previous animation's start |

### Timeline methods

- `.add(targets, params, position?)` - add an animation
- `.add(timerParams, position?)` - add a bare timer
- `.sync(otherTimeline, position?)` - nest another timeline
- `.label(name, position?)` - mark a position
- `.call(fn, position?)` - fire a callback at a position

Timelines share the same control methods (`play`, `pause`, `seek`, `reverse`, …).

## v3 → v4 mapping (do not emit the left column)

| v3 (old - do NOT use) | v4 (use this) |
|---|---|
| `import anime from 'animejs'` | `import { animate } from 'animejs'` |
| `anime({ targets: '.b', x: 100 })` | `animate('.b', { x: 100 })` |
| `anime.timeline()` | `createTimeline()` |
| `anime.stagger(100)` | `stagger(100)` (import `{ stagger }`) |
| `easing: 'easeInOutQuad'` | `ease: 'inOutQuad'` |
| `elasticity` / `round` options | eases args, e.g. `'outElastic(1, .3)'`; `utils.round` |
| keyframe `{ value: x }` | keyframe `{ to: x }` |

## Source

- Animation: https://animejs.com/documentation/animation/
- Timer: https://animejs.com/documentation/timer/
- Timeline: https://animejs.com/documentation/timeline/
- v3→v4 migration: https://github.com/juliangarnier/anime/wiki/Migrating-from-v3-to-v4

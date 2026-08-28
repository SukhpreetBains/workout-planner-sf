# Interaction - draggable, scroll, animatable

## `onScroll(parameters)` - scroll-triggered / scroll-linked

Pass `onScroll({...})` as the `autoplay` value of an animation (or timeline). The animation
plays when its trigger scrolls into view, and can be **synced** to scroll position.

```js
import { animate, onScroll } from 'animejs';

// Play once when it enters the viewport
animate('.reveal', {
  y: [40, 0],
  opacity: [0, 1],
  ease: 'outExpo',
  duration: 700,
  autoplay: onScroll({
    enter: 'bottom top',   // trigger when target bottom hits viewport top area
    leave: 'top bottom',
    once: true,
  }),
});

// Scrub the animation to scroll position (parallax-style)
animate('.parallax', {
  y: 300,
  autoplay: onScroll({
    target: '.section',    // element whose scroll drives it (defaults to animated el)
    container: window,     // scroll container
    sync: true,            // link progress to scroll; also: a number, or an ease name
    onEnter: () => {},
    onLeave: () => {},
    onUpdate: self => {},
  }),
});
```

- `enter` / `leave` - thresholds as `'<target edge> <container edge>'` (e.g. `'bottom top'`,
  `'center center'`, or `'top 80%'`).
- `sync` - `true` links progress 1:1 to scroll; a number smooths it; an ease name eases it;
  omit for play-through-once behavior.
- `once` - play a single time and stop observing.
- `axis` - `'y'` (default) or `'x'`.

## `createDraggable(target, parameters)`

Makes elements draggable with inertia and spring release.

```js
import { createDraggable, createSpring } from 'animejs';

createDraggable('.card', {
  container: '#board',              // constrain within this element
  x: { min: 0, max: 500 },         // per-axis bounds (or `x: false` to lock)
  y: true,
  snap: 50,                        // snap grid on release
  velocityMultiplier: 1.2,
  releaseEase: createSpring({ stiffness: 120, damping: 8 }),
  onGrab:    () => {},
  onDrag:    self => {},
  onRelease: () => {},
  onSnap:    () => {},
  onSettle:  () => {},
});
```

Key params: `container`, `containerPadding`, `containerFriction`, `trigger`, `snap`, `modifier`,
`velocityMultiplier`, `min/maxVelocity`, `dragThreshold`, `cursor`, and the `release*` spring
settings (`releaseStiffness`, `releaseDamping`, `releaseMass`, `releaseEase`).

Instance methods: `enable()`, `disable()`, `setX(n)`, `setY(n)`, `stop()`, `reset()`.

## `createAnimatable(target, parameters)`

For high-frequency, imperative updates (e.g. cursor-following) - you set values directly and
each animates independently, instead of firing a full `animate()` per event.

```js
import { createAnimatable, utils } from 'animejs';

const el = createAnimatable('.cursor', {
  x: 500,               // per-property duration in ms
  y: 500,
  ease: 'out(3)',
});

window.addEventListener('mousemove', e => {
  el.x(e.clientX);      // setter - smoothly animates toward the value
  el.y(e.clientY);
});

const current = el.x();  // getter - read current value
```

Each animated property becomes a getter/setter function. Params per property: a `duration`
number, plus shared `ease`, `unit`, `modifier`.

## Source

- Scroll observer: https://animejs.com/documentation/scroll-observer/
- Draggable: https://animejs.com/documentation/draggable/
- Animatable: https://animejs.com/documentation/animatable/

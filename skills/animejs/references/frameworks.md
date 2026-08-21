# Framework integration & cleanup

**The #1 real-world footgun:** animations created in a component keep running (and hold DOM
references) after the component unmounts. Always wrap animations in a **`createScope`** and call
`scope.revert()` on teardown. `createScope` also centralizes `defaults`, a `root` for scoping
selectors, and responsive `mediaQueries`.

## `createScope(parameters)`

```js
import { animate, utils, createScope } from 'animejs';

const scope = createScope({
  root,                         // element (or ref) that scopes all selectors
  defaults: { ease: 'outExpo' },
  mediaQueries: {
    isSmall: '(max-width: 640px)',
    reduceMotion: '(prefers-reduced-motion)',
  },
}).add(self => {
  const { isSmall, reduceMotion } = self.matches;

  if (reduceMotion) return;                 // respect user preference
  animate('.square', {
    x: isSmall ? 0 : ['-35vw', '35vw'],
    duration: 1250,
  });
});

// later, on teardown:
scope.revert();   // stops animations, reverts inline styles, removes listeners
```

`self.add('name', fn)` can also register callable methods you invoke later (e.g. from an event).

## React

Use `useRef` for the root and create the scope inside `useEffect`, returning
`() => scope.revert()` as the cleanup.

```jsx
import { useEffect, useRef } from 'react';
import { animate, createScope, stagger } from 'animejs';

function Cards() {
  const root = useRef(null);
  const scope = useRef(null);

  useEffect(() => {
    scope.current = createScope({ root }).add(() => {
      animate('.card', {
        y: [24, 0],
        opacity: [0, 1],
        delay: stagger(80),
        ease: 'outExpo',
      });
    });

    return () => scope.current.revert();   // cleanup on unmount
  }, []);

  return (
    <div ref={root}>
      <div className="card">A</div>
      <div className="card">B</div>
    </div>
  );
}
```

Notes:
- Selectors inside the scope resolve **within `root`**, so they won't leak to other components.
- React 18 StrictMode mounts effects twice in dev; `scope.revert()` in cleanup makes this safe.
- To trigger animations later (on state/events), register methods with `self.add('play', fn)`
  inside the scope and call `scope.current.methods.play()`.

## Vue 3

Create the scope in `onMounted`, revert in `onUnmounted`, using a template ref as the root.

```vue
<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { animate, createScope, stagger } from 'animejs';

const root = ref(null);
let scope;

onMounted(() => {
  scope = createScope({ root }).add(() => {
    animate('.card', { y: [24, 0], opacity: [0, 1], delay: stagger(80), ease: 'outExpo' });
  });
});

onUnmounted(() => scope?.revert());
</script>

<template>
  <div ref="root">
    <div class="card">A</div>
    <div class="card">B</div>
  </div>
</template>
```

## Vanilla / SPA routing

Even without a framework, use a scope when you remove DOM (e.g. client-side route changes) so
old animations are cleaned up:

```js
const scope = createScope({ root: '#view' }).add(() => {
  animate('.hero', { opacity: [0, 1], ease: 'outExpo' });
});
// before swapping the view:
scope.revert();
```

## Accessibility - `prefers-reduced-motion`

Always honor reduced-motion. Either gate with the `reduceMotion` media query above, or set
`engine`/durations to 0:

```js
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
animate('.box', { x: 100, duration: reduce ? 0 : 800 });
```

## Source

- Scope: https://animejs.com/documentation/scope/
- WAAPI / frameworks overview: https://animejs.com/documentation/

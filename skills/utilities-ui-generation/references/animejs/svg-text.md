# SVG & Text effects

## SVG utilities

Import as a namespace or individually:

```js
import { svg } from 'animejs';                              // svg.morphTo, svg.createDrawable…
import { morphTo, createDrawable, createMotionPath } from 'animejs';   // named
import { morphTo, createDrawable, createMotionPath } from 'animejs/svg'; // subpath
```

### Line drawing - `createDrawable`

Wraps stroked paths so you can animate the `draw` property from `'0 0'` (hidden) to `'0 1'`
(fully drawn). `draw` is a `"start end"` pair of 0–1 fractions.

```js
import { animate, svg } from 'animejs';

const [drawable] = svg.createDrawable('.path');   // returns proxy targets

animate(drawable, {
  draw: ['0 0', '0 1'],   // draw the line on
  ease: 'inOutQuad',
  duration: 1500,
  loop: true,
});
```

### Morphing - `morphTo`

Animate one path's `d` into the shape of another (paths should have compatible point counts).

```js
import { animate, svg } from 'animejs';

animate('.shape-a', {
  d: svg.morphTo('.shape-b'),   // morph path A to match path B
  ease: 'inOut',
  duration: 800,
});
```

### Motion path - `createMotionPath`

Move an element along an SVG path. Returns `{ x, y, angle }` value functions to feed into
`animate`.

```js
import { animate, svg } from 'animejs';

const { x, y, angle } = svg.createMotionPath('.path');

animate('.dot', {
  x, y,
  rotate: angle,   // orient the element along the path
  ease: 'linear',
  duration: 2000,
  loop: true,
});
```

## Text utilities

```js
import { text } from 'animejs';                       // text.splitText, text.scrambleText
import { splitText, scrambleText } from 'animejs';    // named
import { splitText, scrambleText } from 'animejs/text'; // subpath
```

### `splitText` - animate per character / word / line

Splits an element's text into wrapped spans you can target and stagger.

```js
import { animate, stagger, splitText } from 'animejs';

const { chars, words, lines } = splitText('h1', {
  chars: true,
  words: false,
  lines: false,
});

animate(chars, {
  y: [40, 0],
  opacity: [0, 1],
  ease: 'outExpo',
  duration: 700,
  delay: stagger(40),        // ripple across characters
});
```

Options: `chars`, `words`, `lines`, `includeSpaces`, `accessible` (keeps original text for
screen readers), `debug`, plus markup controls (`class`, `wrap`, `clone`).

### `scrambleText` - decode/scramble reveal

```js
import { scrambleText } from 'animejs';

scrambleText('.title', {
  chars: '!<>-_\\/[]{}=+*^?#',
  duration: 800,
  ease: 'inOutQuad',
});
```

## Source

- SVG: https://animejs.com/documentation/svg/
- Text: https://animejs.com/documentation/text/

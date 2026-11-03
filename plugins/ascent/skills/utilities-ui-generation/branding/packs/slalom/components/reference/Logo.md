# Logo

The Slalom wordmark, one of the four approved files, with its clear space built in. Set `--sl-logo-h` (px, at least 9px) and the wrapper adds padding of 0.76 × that height on every side, the width of the "o".

Pick the file by ground: `slalom-logo-blue-RGB.svg` or `slalom-logo-dark-blue-RGB.svg` on white, light gray or a secondary color; `slalom-logo-white-RGB.svg` (preferred) or black reversed on Slalom Blue, Slalom Dark Blue, Coral Red or dark tones; black only in black-and-white layouts. On `data-theme="dark"` use white. Never scale the image beyond `--sl-logo-h`, add effects, or put anything inside the clear space.

## Markup

```html
<span class="sl-logo" style="--sl-logo-h:32px"><img src="../assets/logos/slalom-logo-blue-RGB.svg" alt="Slalom"></span>
```

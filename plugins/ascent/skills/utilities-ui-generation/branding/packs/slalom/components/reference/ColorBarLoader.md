# ColorBarLoader

The color bar brought to life: five circles in the bar's fixed order, bobbing in sequence. `--sl-dot` sets the circle size (default 12px); `aria-label` names it for assistive technology.

Use it for page- or section-level loading. It counts as the layout's one color bar, so do not show a `ColorBar` on the same view while it runs. Under `prefers-reduced-motion` the circles hold still.

## Markup

```html
<span class="sl-cbloader" role="status" aria-label="Loading" style="--sl-dot:12px">
  <span class="sl-cbloader-dot" style="background:var(--slalom-blue)"></span>
  <span class="sl-cbloader-dot" style="background:var(--cyan);animation-delay:.15s"></span>
  <span class="sl-cbloader-dot" style="background:var(--coral-red);animation-delay:.3s"></span>
  <span class="sl-cbloader-dot" style="background:var(--purple);animation-delay:.45s"></span>
  <span class="sl-cbloader-dot" style="background:var(--chartreuse);animation-delay:.6s"></span>
</span>
```

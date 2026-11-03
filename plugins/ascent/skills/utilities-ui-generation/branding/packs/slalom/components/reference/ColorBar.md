# ColorBar

The official five-swatch bar: Slalom Blue, Cyan, Coral Red, Purple, Chartreuse, in that order, equal widths. Thin bars are 4–12px; a thick bar may take up to 20% of the layout, never more. When the layout ground is one of the five colors, change only that swatch to its Dark 3 tone (for example `var(--purple-dark-3)`). Add `sl-bar-framing sl-bar-framing-top` (or `-bottom`, `-left`, `-right`) to pin it to one edge of a `position: relative` parent; for left and right set `width` instead of `height`.

One bar per layout. Never reorder, recolor, animate or drop a swatch. It is the one place all five colors appear together outside infographics.

## Markup

```html
<div class="sl-bar" role="presentation" style="height:8px">
  <span class="sl-bar-swatch" style="background:var(--slalom-blue)"></span>
  <span class="sl-bar-swatch" style="background:var(--cyan)"></span>
  <span class="sl-bar-swatch" style="background:var(--coral-red)"></span>
  <span class="sl-bar-swatch" style="background:var(--purple)"></span>
  <span class="sl-bar-swatch" style="background:var(--chartreuse)"></span>
</div>
```

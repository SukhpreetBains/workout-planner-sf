# Reveal

Fades and rises any block into place as it scrolls into view. `data-from="up"` (default), `"left"` or `"none"`; `data-delay` in ms; `data-threshold` (0–1). With `data-stagger` (ms), each direct child reveals in turn: card rows, stat rows, lists.

Use it to pace a long page; reveal each block once, 24px of travel. Never hide essential content behind it. Without the script, or under reduced motion, content is simply there.

## Markup

```html
<div class="sl-row" data-sl="reveal" data-stagger="120">
  <div class="sl-card sl-card-surface sl-corner-br sl-radius-m"><p class="sl-card-eyebrow eyebrow">Discover</p><h3 class="sl-card-title headline-m">Listen first</h3></div>
  <div class="sl-card sl-card-cyan sl-corner-br sl-radius-m"><p class="sl-card-eyebrow eyebrow">Define</p><h3 class="sl-card-title headline-m">Shape it together</h3></div>
  <div class="sl-card sl-card-surface sl-corner-br sl-radius-m"><p class="sl-card-eyebrow eyebrow">Deliver</p><h3 class="sl-card-title headline-m">Build momentum</h3></div>
</div>
```

# Card

The brand's one-rounded-corner surface. Tone: `sl-card-surface` (hairline border), `sl-card-raised` (light gray), `sl-card-accent` (Slalom Blue, white text) or one secondary (`sl-card-cyan`, `-purple`, `-chartreuse` with Slalom Dark Blue text; `-coral-red` with black). Corner: `sl-corner-tl|tr|bl|br`. Size: `sl-radius-s|m|l`.

One tone family per composition: a Slalom Blue card beside surface cards, or surface cards beside one secondary, never two secondaries. Round exactly one corner.

## Markup

```html
<div class="sl-card sl-card-surface sl-corner-br sl-radius-m">
  <p class="sl-card-eyebrow eyebrow">Discover</p>
  <h3 class="sl-card-title headline-m">Listen first</h3>
  <p class="body">Understand people before process.</p>
</div>
```

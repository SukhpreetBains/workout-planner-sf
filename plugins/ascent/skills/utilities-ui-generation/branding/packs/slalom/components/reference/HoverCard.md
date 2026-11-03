# HoverCard

A white card with a hairline border that fills Slalom Blue on hover or keyboard focus. Make it an `<a>` (or give a `<div>` `tabindex="0"`) so the hover means something, and give it a CTA line. After Uiverse `suleymanlaarabidev/perfect-husky-88` (MIT), shadow and all-round radius removed.

Use it for navigational tiles: services, industries, stories, deliverable sections. The fill is the composition's Slalom Blue; keep other blue accents around it quiet.

## Markup

```html
<a class="sl-hcard sl-corner-br sl-radius-m" href="#">
  <p class="sl-hcard-eyebrow eyebrow">Service</p>
  <h3 class="sl-hcard-title headline-m">Artificial intelligence</h3>
  <div class="sl-hcard-body body"><p>Machine learning, generative AI and intelligent products.</p></div>
  <span class="sl-hcard-cta body-strong">Explore →</span>
</a>
```

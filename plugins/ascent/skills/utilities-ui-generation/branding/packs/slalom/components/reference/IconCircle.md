# IconCircle

An approved icon on a colored circle, for use over images and busy layouts. The circle takes one secondary color (never Slalom Blue or Slalom Dark Blue); the icon on it is always Slalom Dark Blue (the `sl-icon-mask` default) at 56% of the circle's diameter. Keep the circle at least 86px so the icon meets the 48px minimum. One circle tone per layout, the composition's one secondary.

## Markup

```html
<span class="sl-icon-circle" style="width:96px;height:96px;background:var(--cyan)">
  <span class="sl-icon-mask" aria-hidden="true" style="--sl-icon:url('../assets/iconography/award.svg');--sl-icon-size:54px"></span>
</span>
```

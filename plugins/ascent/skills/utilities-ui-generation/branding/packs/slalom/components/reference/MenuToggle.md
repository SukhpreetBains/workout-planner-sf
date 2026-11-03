# MenuToggle

A 40px button whose three bars become an X. The script adds the bars, keeps `aria-expanded` and the label ("Open menu" / "Close menu") in step, toggles `hidden` on the element named by `aria-controls`, and fires a bubbling `sl:toggle` event with `detail.open`. Add `sl-menu-on-accent` for white bars on a Slalom Blue or black header.

## Markup

```html
<button type="button" class="sl-menu" data-sl="menu-toggle" aria-label="Open menu" aria-controls="site-menu"></button>
<nav id="site-menu" hidden>…</nav>
```

# Button

A rectangular action with a Slalom Sans Regular label in sentence case. `sl-btn-primary` is Slalom Blue and darkens to Slalom Dark Blue on hover; `sl-btn-secondary` is an ink outline that underlines on hover; `sl-btn-on-accent` is white with Slalom Dark Blue text, for a Slalom Blue or black ground. Works on `<a>` too.

One primary per view. Square corners, no shadow, no gradient; an icon-only button needs an `aria-label`. Never make a secondary-color button: it would spend the composition's one accent on a control.

## Markup

```html
<button type="button" class="sl-btn sl-btn-primary">Explore the roadmap</button>
<button type="button" class="sl-btn sl-btn-secondary">Let’s talk</button>
```

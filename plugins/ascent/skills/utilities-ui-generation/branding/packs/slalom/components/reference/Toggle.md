# Toggle

An on/off switch: a rectangular track with a square thumb that shows a check when on, so state never relies on color alone. The native checkbox carries `role="switch"`, so keyboard and screen readers work without script. Use it for a setting that applies at once; use `Checkbox` for choices submitted with a form.

## Markup

```html
<label class="sl-toggle"><input class="sl-toggle-input" type="checkbox" role="switch" checked><span class="sl-toggle-track" aria-hidden="true"><span class="sl-toggle-thumb"></span></span><span class="sl-toggle-label body-strong">Show sources</span></label>
```

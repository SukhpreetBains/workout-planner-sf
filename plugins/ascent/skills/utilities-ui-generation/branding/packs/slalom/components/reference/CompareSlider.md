# CompareSlider

Two panels in one frame with a handle the reader drags to wipe between them: before on the left, after on the right. `data-before-label`, `data-after-label`, `data-initial` (0–100), `data-label`. Height defaults to 360px; set `height` on the element to change it. The handle is a real range input, so arrow keys work.

For current-state versus future-state moments. Keep the two panels the same layout, and keep each panel's copy within its own half (as the `max-width: 40%` does here), so the change is what the eye catches.

## Markup

```html
<div class="sl-cmp" data-sl="compare" data-before-label="Today" data-after-label="Tomorrow">
  <div class="sl-cmp-layer sl-cmp-after"><div style="background:var(--slalom-blue);color:var(--white);padding:var(--space-6) var(--space-5);display:flex;flex-direction:column;align-items:flex-end;text-align:right"><p class="headline-m" style="max-width:40%">Five weeks to onboard</p><p class="body" style="max-width:40%">One portal, guided from day one.</p></div></div>
  <div class="sl-cmp-layer sl-cmp-before"><div style="background:var(--light-gray);color:var(--black);padding:var(--space-6) var(--space-5)"><p class="headline-m" style="max-width:40%">Nine weeks to onboard</p><p class="body" style="max-width:40%">Five systems, three logins and a binder of how-tos.</p></div></div>
</div>
```

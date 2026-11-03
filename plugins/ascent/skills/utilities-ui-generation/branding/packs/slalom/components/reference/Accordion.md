# Accordion

Hairline rows with a numbered title; the square plus turns to a minus and fills Slalom Blue as the panel eases open. `data-open` lists the rows open at first (indexes), `data-multiple` lets several stay open, `data-numbered="false"` drops the numbers. The script turns each heading into a real button with `aria-expanded`; closed panels are inert. Without the script every panel shows.

For FAQs, assumptions, scope details and appendix content.

## Markup

```html
<div class="sl-acc" data-sl="accordion" data-open="0">
  <div class="sl-acc-item"><h3 class="sl-acc-h">What does the first month look like?</h3><div class="sl-acc-panel"><div class="sl-acc-inner body"><p>We spend it listening: interviews, a look at your data, and a shared view of success.</p></div></div></div>
  <div class="sl-acc-item"><h3 class="sl-acc-h">Who will we work with?</h3><div class="sl-acc-panel"><div class="sl-acc-inner body"><p>A small, senior Slalom team alongside your product owners.</p></div></div></div>
  <div class="sl-acc-item"><h3 class="sl-acc-h">How do we measure progress?</h3><div class="sl-acc-panel"><div class="sl-acc-inner body"><p>Three to five measures agreed in week two, reported every sprint review.</p></div></div></div>
</div>
```

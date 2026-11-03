# WaffleStat

A 10 × 10 grid of squares where the share fills in Slalom Blue cell by cell, beside a counting figure. `data-value` (0–100). The grid is announced as "62 of 100" plus the label; the number and words carry the meaning, never color alone.

Use it when a share of people is the story. One per section.

## Markup

```html
<figure class="sl-waffle" data-sl="waffle" data-value="62">
  <figcaption class="sl-waffle-text">
    <span class="sl-waffle-num">62<span class="sl-stat-suffix">%</span></span>
    <span class="sl-waffle-label subhead">of customers</span>
    <span class="sl-waffle-caption body">say they would switch providers after one poor digital experience.</span>
  </figcaption>
</figure>
```

# StatCounter

A big Slalom Blue figure that counts up once in view. `data-value`, `data-prefix` ("$"), `data-suffix` ("%", "M", "x"), `data-decimals`, `data-duration` (ms), and `data-bar` (0–100) to add a bar that fills to that share. Write the final figure inside `.sl-stat-num` so it reads without the script; screen readers hear only the final value.

Two to four in a row for headline results. Every number real and sourced, never filler. Brand number style: digits from 10, `%` with no space, short forms for big figures ($2.4M).

## Markup

```html
<div class="sl-stat" data-sl="stat" data-value="44" data-suffix="%" data-bar="44">
  <p class="sl-stat-label eyebrow">Faster onboarding</p>
  <p class="sl-stat-num">44%</p>
  <p class="sl-stat-caption body">New hires reach full productivity in five weeks, down from nine.</p>
</div>
```
